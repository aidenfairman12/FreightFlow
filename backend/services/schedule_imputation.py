"""
Flight schedule imputation for offline periods.

SWISS operates a highly regular weekly schedule. This service:
1. Learns schedule patterns from observed flight data (callsign + day-of-week + time).
2. Detects offline gaps (periods where no state_vectors were recorded).
3. Generates imputed "expected" flights for the gap.
4. Reconciles imputed flights when real data confirms/denies them.

Imputed flights live in a separate table — never mixed with real observations.
"""

import logging
from datetime import datetime, timedelta, time as dt_time

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services import swiss_routes

logger = logging.getLogger(__name__)

# Minimum observations before a pattern is used for imputation
MIN_CONFIDENCE_OBSERVATIONS = 3
# How close (in hours) a real flight must be to an imputed one to "match"
MATCH_WINDOW_HOURS = 3
# How many days back to look when learning patterns
LEARNING_LOOKBACK_DAYS = 30
# Confidence formula: min(observations / CONFIDENCE_THRESHOLD, 1.0)
CONFIDENCE_THRESHOLD = 10


async def learn_schedule_patterns() -> int:
    """
    Analyze completed flights to build/update weekly schedule patterns.

    Groups flights by normalized callsign and ISO day-of-week, computing
    the median departure time and observation count. Updates existing
    patterns or inserts new ones.

    Returns count of patterns updated/created.
    """
    async with AsyncSessionLocal() as session:
        # Get flight patterns from the last N days
        result = await session.execute(text("""
            WITH flight_patterns AS (
                SELECT
                    -- Normalize callsign: strip trailing letter suffix
                    UPPER(REGEXP_REPLACE(callsign, '([A-Z])$', '')) AS callsign_norm,
                    EXTRACT(ISODOW FROM first_seen)::int - 1 AS day_of_week,  -- 0=Mon
                    first_seen::time AS departure_time,
                    origin_icao,
                    destination_icao,
                    first_seen
                FROM flights
                WHERE first_seen > NOW() - INTERVAL :lookback_days
                  AND callsign IS NOT NULL
                  AND callsign ~ '^SWR\\d+'
            ),
            aggregated AS (
                SELECT
                    callsign_norm,
                    day_of_week,
                    -- Median departure time (via percentile_cont)
                    -- Convert time to seconds-since-midnight for aggregation
                    MAKE_TIME(
                        (PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY EXTRACT(EPOCH FROM departure_time)
                        ) / 3600)::int,
                        ((PERCENTILE_CONT(0.5) WITHIN GROUP (
                            ORDER BY EXTRACT(EPOCH FROM departure_time)
                        )::int % 3600) / 60),
                        0
                    ) AS typical_departure_utc,
                    MODE() WITHIN GROUP (ORDER BY origin_icao) AS origin_icao,
                    MODE() WITHIN GROUP (ORDER BY destination_icao) AS destination_icao,
                    COUNT(*) AS obs_count,
                    MAX(first_seen) AS last_observed
                FROM flight_patterns
                WHERE callsign_norm IS NOT NULL
                GROUP BY callsign_norm, day_of_week
            )
            INSERT INTO flight_schedule_patterns
                (callsign_norm, day_of_week, typical_departure_utc,
                 origin_icao, destination_icao, observation_count,
                 confidence, last_observed, updated_at)
            SELECT
                callsign_norm, day_of_week, typical_departure_utc,
                origin_icao, destination_icao, obs_count,
                LEAST(obs_count::double precision / :conf_threshold, 1.0),
                last_observed, NOW()
            FROM aggregated
            ON CONFLICT (callsign_norm, day_of_week) DO UPDATE SET
                typical_departure_utc = EXCLUDED.typical_departure_utc,
                origin_icao = EXCLUDED.origin_icao,
                destination_icao = EXCLUDED.destination_icao,
                observation_count = EXCLUDED.observation_count,
                confidence = EXCLUDED.confidence,
                last_observed = EXCLUDED.last_observed,
                updated_at = NOW()
            RETURNING id
        """), {
            "lookback_days": f"{LEARNING_LOOKBACK_DAYS} days",
            "conf_threshold": CONFIDENCE_THRESHOLD,
        })
        rows = result.fetchall()
        await session.commit()

        count = len(rows)
        if count > 0:
            logger.info("Updated %d schedule patterns from observed flights", count)
        return count


async def detect_offline_gap() -> tuple[datetime | None, datetime | None]:
    """
    Detect the most recent offline gap by finding when state_vectors stopped
    and when they resumed.

    Returns (gap_start, gap_end) or (None, None) if no significant gap.
    A gap is "significant" if >20 minutes with no data (normal poll is 10-30s).
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            WITH ordered AS (
                SELECT
                    time,
                    LEAD(time) OVER (ORDER BY time) AS next_time
                FROM (
                    -- Sample: get one row per minute to avoid scanning millions
                    SELECT DISTINCT ON (date_trunc('minute', time)) time
                    FROM state_vectors
                    WHERE time > NOW() - INTERVAL '7 days'
                    ORDER BY date_trunc('minute', time), time
                ) sampled
            )
            SELECT
                time AS gap_start,
                next_time AS gap_end,
                EXTRACT(EPOCH FROM next_time - time) / 60 AS gap_minutes
            FROM ordered
            WHERE next_time - time > INTERVAL '20 minutes'
            ORDER BY next_time DESC
            LIMIT 1
        """))
        row = result.fetchone()
        if row:
            return row[0], row[1]
        return None, None


async def impute_offline_flights(
    gap_start: datetime, gap_end: datetime
) -> int:
    """
    Generate imputed flight records for an offline gap period.

    For each day (or partial day) in the gap, looks up schedule patterns
    for that day-of-week and creates "expected" imputed_flights entries
    for flights that would have occurred.

    Only uses patterns with sufficient confidence (MIN_CONFIDENCE_OBSERVATIONS).
    Returns count of imputed flights created.
    """
    async with AsyncSessionLocal() as session:
        # Get all patterns with sufficient confidence
        result = await session.execute(text("""
            SELECT callsign_norm, day_of_week, typical_departure_utc,
                   origin_icao, destination_icao, confidence
            FROM flight_schedule_patterns
            WHERE observation_count >= :min_obs
            ORDER BY callsign_norm, day_of_week
        """), {"min_obs": MIN_CONFIDENCE_OBSERVATIONS})
        patterns = result.fetchall()

        if not patterns:
            logger.info("No schedule patterns with sufficient confidence for imputation")
            return 0

        # Build lookup: day_of_week -> list of patterns
        by_dow: dict[int, list] = {}
        for p in patterns:
            dow = p[1]
            by_dow.setdefault(dow, []).append(p)

        # Walk through each day in the gap
        count = 0
        current_date = gap_start.date()
        end_date = gap_end.date()

        while current_date <= end_date:
            # ISO weekday: Monday=0 ... Sunday=6
            dow = current_date.weekday()
            day_patterns = by_dow.get(dow, [])

            for p in day_patterns:
                callsign_norm, _, typical_time, origin, dest, confidence = p
                # Build expected datetime
                expected_dt = datetime.combine(current_date, typical_time)

                # Only impute if this time falls within the gap
                if expected_dt < gap_start or expected_dt > gap_end:
                    continue

                # Check if we already imputed this flight
                existing = await session.execute(text("""
                    SELECT id FROM imputed_flights
                    WHERE callsign_norm = :cs
                      AND expected_time = :et
                """), {"cs": callsign_norm, "et": expected_dt})
                if existing.fetchone():
                    continue

                await session.execute(text("""
                    INSERT INTO imputed_flights
                        (callsign_norm, expected_time, origin_icao,
                         destination_icao, status, pattern_confidence)
                    VALUES (:cs, :et, :origin, :dest, 'expected', :conf)
                """), {
                    "cs": callsign_norm,
                    "et": expected_dt,
                    "origin": origin,
                    "dest": dest,
                    "conf": confidence,
                })
                count += 1

            current_date += timedelta(days=1)

        await session.commit()
        if count > 0:
            logger.info(
                "Imputed %d expected flights for offline gap %s to %s",
                count, gap_start.isoformat(), gap_end.isoformat(),
            )
        return count


async def reconcile_imputed_flights() -> dict[str, int]:
    """
    Match imputed flights against real flight data.

    For each 'expected' imputed flight:
    - If a real flight with the same callsign exists within MATCH_WINDOW_HOURS
      of the expected time -> mark 'confirmed', link to the real flight.
    - If the expected time is >MATCH_WINDOW_HOURS in the past with no match
      -> mark 'missed'.

    Returns {"confirmed": N, "missed": N}.
    """
    async with AsyncSessionLocal() as session:
        # Confirm: match imputed flights to real flights
        confirmed = await session.execute(text("""
            UPDATE imputed_flights imp
            SET status = 'confirmed',
                matched_flight_id = matched.flight_id,
                reconciled_at = NOW()
            FROM (
                SELECT DISTINCT ON (imp.id)
                    imp.id AS imp_id,
                    f.flight_id
                FROM imputed_flights imp
                JOIN flights f ON
                    UPPER(REGEXP_REPLACE(f.callsign, '([A-Z])$', '')) = imp.callsign_norm
                    AND ABS(EXTRACT(EPOCH FROM f.first_seen - imp.expected_time)) < :window_sec
                WHERE imp.status = 'expected'
                ORDER BY imp.id, ABS(EXTRACT(EPOCH FROM f.first_seen - imp.expected_time))
            ) matched
            WHERE imp.id = matched.imp_id
            RETURNING imp.id
        """), {"window_sec": MATCH_WINDOW_HOURS * 3600})
        confirmed_count = len(confirmed.fetchall())

        # Mark old unmatched as missed (only if well past the match window)
        missed = await session.execute(text("""
            UPDATE imputed_flights
            SET status = 'missed', reconciled_at = NOW()
            WHERE status = 'expected'
              AND expected_time < NOW() - INTERVAL :window
            RETURNING id
        """), {"window": f"{MATCH_WINDOW_HOURS} hours"})
        missed_count = len(missed.fetchall())

        await session.commit()

        if confirmed_count or missed_count:
            logger.info(
                "Reconciled imputed flights: %d confirmed, %d missed",
                confirmed_count, missed_count,
            )
        return {"confirmed": confirmed_count, "missed": missed_count}


async def run_imputation_cycle() -> dict:
    """
    Full imputation cycle: learn patterns, detect gaps, impute, reconcile.

    Called periodically (e.g., every hour) or on startup.
    """
    # Step 1: Update schedule patterns from observed data
    patterns_updated = await learn_schedule_patterns()

    # Step 2: Detect any offline gap
    gap_start, gap_end = await detect_offline_gap()

    imputed = 0
    if gap_start and gap_end:
        gap_minutes = (gap_end - gap_start).total_seconds() / 60
        logger.info(
            "Detected offline gap: %s to %s (%.0f min)",
            gap_start.isoformat(), gap_end.isoformat(), gap_minutes,
        )
        # Step 3: Impute flights for the gap
        imputed = await impute_offline_flights(gap_start, gap_end)

    # Step 4: Reconcile all pending imputed flights against real data
    reconciled = await reconcile_imputed_flights()

    return {
        "patterns_updated": patterns_updated,
        "gap_detected": gap_start is not None,
        "gap_start": gap_start.isoformat() if gap_start else None,
        "gap_end": gap_end.isoformat() if gap_end else None,
        "flights_imputed": imputed,
        "reconciled": reconciled,
    }


async def get_schedule_summary() -> list[dict]:
    """Return the current learned schedule for API/UI display."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT callsign_norm, day_of_week, typical_departure_utc,
                   origin_icao, destination_icao, observation_count,
                   confidence, last_observed
            FROM flight_schedule_patterns
            WHERE observation_count >= :min_obs
            ORDER BY day_of_week, typical_departure_utc
        """), {"min_obs": MIN_CONFIDENCE_OBSERVATIONS})
        rows = result.fetchall()

        days = ["Monday", "Tuesday", "Wednesday", "Thursday",
                "Friday", "Saturday", "Sunday"]
        return [
            {
                "callsign": r[0],
                "day_of_week": days[r[1]],
                "departure_utc": r[2].strftime("%H:%M") if r[2] else None,
                "origin": r[3],
                "destination": r[4],
                "observations": r[5],
                "confidence": round(r[6], 2),
                "last_observed": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]


async def get_imputed_flights(
    status: str | None = None, limit: int = 100
) -> list[dict]:
    """Return imputed flights, optionally filtered by status."""
    async with AsyncSessionLocal() as session:
        query = """
            SELECT callsign_norm, expected_time, origin_icao,
                   destination_icao, status, pattern_confidence,
                   matched_flight_id, reconciled_at
            FROM imputed_flights
        """
        params: dict = {"limit": limit}
        if status:
            query += " WHERE status = :status"
            params["status"] = status
        query += " ORDER BY expected_time DESC LIMIT :limit"

        result = await session.execute(text(query), params)
        rows = result.fetchall()

        return [
            {
                "callsign": r[0],
                "expected_time": r[1].isoformat() if r[1] else None,
                "origin": r[2],
                "destination": r[3],
                "status": r[4],
                "confidence": round(r[5], 2) if r[5] else None,
                "matched_flight_id": str(r[6]) if r[6] else None,
                "reconciled_at": r[7].isoformat() if r[7] else None,
            }
            for r in rows
        ]
