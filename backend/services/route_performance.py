"""
Route performance analysis: baselines vs actuals.

Computes per-route performance metrics by comparing recent flights against
historical baselines (duration, fuel burn, CO2). Routes are scored and
categorized as overperforming, average, or underperforming.

Used for:
- Identifying inefficient routes for operational improvements
- Feeding ML models with route-level performance features
- Supporting scenario engine route suggestions
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# How many days of recent data to compare against baseline
RECENT_WINDOW_DAYS = 7
# Minimum flights before a route gets scored
MIN_FLIGHTS_FOR_BASELINE = 3
MIN_RECENT_FLIGHTS = 2


async def compute_route_performance() -> int:
    """
    Compute performance metrics for all SWISS routes with sufficient data.

    For each route (origin→destination pair):
    1. Compute all-time baselines (avg duration, fuel, CO2)
    2. Compute recent-window actuals (last 7 days)
    3. Calculate deviation percentages
    4. Score and categorize

    Returns count of routes scored.
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            WITH baseline AS (
                -- All-time averages per route
                SELECT
                    origin_icao,
                    destination_icao,
                    COUNT(*) AS total_flights,
                    AVG(EXTRACT(EPOCH FROM last_seen - first_seen) / 60)
                        AS avg_duration_min,
                    STDDEV(EXTRACT(EPOCH FROM last_seen - first_seen) / 60)
                        AS std_duration_min,
                    AVG(total_fuel_kg) AS avg_fuel_kg,
                    STDDEV(total_fuel_kg) AS std_fuel_kg,
                    AVG(total_co2_kg) AS avg_co2_kg,
                    AVG(distance_km) AS avg_distance_km
                FROM flights
                WHERE origin_icao IS NOT NULL
                  AND destination_icao IS NOT NULL
                  AND first_seen IS NOT NULL
                  AND last_seen IS NOT NULL
                  AND callsign LIKE 'SWR%'
                GROUP BY origin_icao, destination_icao
                HAVING COUNT(*) >= :min_flights
            ),
            recent AS (
                -- Recent window averages
                SELECT
                    origin_icao,
                    destination_icao,
                    COUNT(*) AS recent_flights,
                    AVG(EXTRACT(EPOCH FROM last_seen - first_seen) / 60)
                        AS avg_duration_min,
                    AVG(total_fuel_kg) AS avg_fuel_kg,
                    AVG(total_co2_kg) AS avg_co2_kg
                FROM flights
                WHERE origin_icao IS NOT NULL
                  AND destination_icao IS NOT NULL
                  AND first_seen > NOW() - INTERVAL :recent_days
                  AND callsign LIKE 'SWR%'
                GROUP BY origin_icao, destination_icao
                HAVING COUNT(*) >= :min_recent
            )
            INSERT INTO route_performance (
                origin_icao, destination_icao,
                baseline_duration_min, baseline_fuel_kg, baseline_co2_kg,
                baseline_distance_km,
                recent_avg_duration_min, recent_avg_fuel_kg, recent_avg_co2_kg,
                recent_flight_count,
                duration_deviation_pct, fuel_deviation_pct, co2_deviation_pct,
                std_duration_min, std_fuel_kg,
                total_flight_count,
                performance_score, category,
                fuel_per_km, co2_per_km,
                updated_at
            )
            SELECT
                b.origin_icao,
                b.destination_icao,
                b.avg_duration_min,
                b.avg_fuel_kg,
                b.avg_co2_kg,
                b.avg_distance_km,
                r.avg_duration_min,
                r.avg_fuel_kg,
                r.avg_co2_kg,
                r.recent_flights,
                -- Deviation %: positive means worse than baseline
                CASE WHEN b.avg_duration_min > 0
                     THEN (r.avg_duration_min - b.avg_duration_min) / b.avg_duration_min * 100
                     ELSE NULL END,
                CASE WHEN b.avg_fuel_kg > 0
                     THEN (r.avg_fuel_kg - b.avg_fuel_kg) / b.avg_fuel_kg * 100
                     ELSE NULL END,
                CASE WHEN b.avg_co2_kg > 0
                     THEN (r.avg_co2_kg - b.avg_co2_kg) / b.avg_co2_kg * 100
                     ELSE NULL END,
                b.std_duration_min,
                b.std_fuel_kg,
                b.total_flights,
                -- Performance score: weighted inverse of deviations
                -- Negative score = underperforming, positive = overperforming
                CASE WHEN b.avg_fuel_kg > 0 AND b.avg_duration_min > 0
                     THEN GREATEST(-1.0, LEAST(1.0,
                         -0.5 * (r.avg_fuel_kg - b.avg_fuel_kg) / NULLIF(b.avg_fuel_kg, 0)
                         -0.3 * (r.avg_duration_min - b.avg_duration_min) / NULLIF(b.avg_duration_min, 0)
                         -0.2 * (r.avg_co2_kg - b.avg_co2_kg) / NULLIF(b.avg_co2_kg, 0)
                     ))
                     ELSE 0.0 END,
                -- Category
                CASE
                    WHEN b.avg_fuel_kg > 0 AND (r.avg_fuel_kg - b.avg_fuel_kg) / b.avg_fuel_kg < -0.05
                         THEN 'overperforming'
                    WHEN b.avg_fuel_kg > 0 AND (r.avg_fuel_kg - b.avg_fuel_kg) / b.avg_fuel_kg > 0.05
                         THEN 'underperforming'
                    ELSE 'average'
                END,
                -- Fuel/CO2 per km
                CASE WHEN b.avg_distance_km > 0
                     THEN b.avg_fuel_kg / b.avg_distance_km ELSE NULL END,
                CASE WHEN b.avg_distance_km > 0
                     THEN b.avg_co2_kg / b.avg_distance_km ELSE NULL END,
                NOW()
            FROM baseline b
            JOIN recent r ON b.origin_icao = r.origin_icao
                         AND b.destination_icao = r.destination_icao
            ON CONFLICT (origin_icao, destination_icao) DO UPDATE SET
                baseline_duration_min = EXCLUDED.baseline_duration_min,
                baseline_fuel_kg = EXCLUDED.baseline_fuel_kg,
                baseline_co2_kg = EXCLUDED.baseline_co2_kg,
                baseline_distance_km = EXCLUDED.baseline_distance_km,
                recent_avg_duration_min = EXCLUDED.recent_avg_duration_min,
                recent_avg_fuel_kg = EXCLUDED.recent_avg_fuel_kg,
                recent_avg_co2_kg = EXCLUDED.recent_avg_co2_kg,
                recent_flight_count = EXCLUDED.recent_flight_count,
                duration_deviation_pct = EXCLUDED.duration_deviation_pct,
                fuel_deviation_pct = EXCLUDED.fuel_deviation_pct,
                co2_deviation_pct = EXCLUDED.co2_deviation_pct,
                std_duration_min = EXCLUDED.std_duration_min,
                std_fuel_kg = EXCLUDED.std_fuel_kg,
                total_flight_count = EXCLUDED.total_flight_count,
                performance_score = EXCLUDED.performance_score,
                category = EXCLUDED.category,
                fuel_per_km = EXCLUDED.fuel_per_km,
                co2_per_km = EXCLUDED.co2_per_km,
                updated_at = NOW()
            RETURNING id
        """), {
            "min_flights": MIN_FLIGHTS_FOR_BASELINE,
            "min_recent": MIN_RECENT_FLIGHTS,
            "recent_days": f"{RECENT_WINDOW_DAYS} days",
        })
        rows = result.fetchall()
        await session.commit()

        count = len(rows)
        if count > 0:
            logger.info("Computed performance metrics for %d routes", count)
        return count


async def get_route_performance_summary(
    category: str | None = None,
    sort_by: str = "performance_score",
    limit: int = 50,
) -> list[dict]:
    """Return route performance data for API/UI display."""
    valid_sorts = {
        "performance_score", "fuel_deviation_pct", "duration_deviation_pct",
        "co2_deviation_pct", "total_flight_count", "fuel_per_km",
    }
    if sort_by not in valid_sorts:
        sort_by = "performance_score"

    async with AsyncSessionLocal() as session:
        query = f"""
            SELECT
                origin_icao, destination_icao,
                baseline_duration_min, baseline_fuel_kg, baseline_co2_kg,
                baseline_distance_km,
                recent_avg_duration_min, recent_avg_fuel_kg, recent_avg_co2_kg,
                recent_flight_count,
                duration_deviation_pct, fuel_deviation_pct, co2_deviation_pct,
                std_duration_min, std_fuel_kg,
                total_flight_count,
                performance_score, category,
                fuel_per_km, co2_per_km,
                updated_at
            FROM route_performance
        """
        params: dict = {"limit": limit}
        if category:
            query += " WHERE category = :category"
            params["category"] = category
        query += f" ORDER BY {sort_by} ASC LIMIT :limit"

        result = await session.execute(text(query), params)
        rows = result.fetchall()

        return [
            {
                "origin": r[0],
                "destination": r[1],
                "baseline": {
                    "duration_min": round(r[2], 1) if r[2] else None,
                    "fuel_kg": round(r[3], 1) if r[3] else None,
                    "co2_kg": round(r[4], 1) if r[4] else None,
                    "distance_km": round(r[5], 1) if r[5] else None,
                },
                "recent": {
                    "duration_min": round(r[6], 1) if r[6] else None,
                    "fuel_kg": round(r[7], 1) if r[7] else None,
                    "co2_kg": round(r[8], 1) if r[8] else None,
                    "flight_count": r[9],
                },
                "deviation": {
                    "duration_pct": round(r[10], 2) if r[10] else None,
                    "fuel_pct": round(r[11], 2) if r[11] else None,
                    "co2_pct": round(r[12], 2) if r[12] else None,
                },
                "variability": {
                    "std_duration_min": round(r[13], 1) if r[13] else None,
                    "std_fuel_kg": round(r[14], 1) if r[14] else None,
                },
                "total_flights": r[15],
                "performance_score": round(r[16], 3) if r[16] else None,
                "category": r[17],
                "efficiency": {
                    "fuel_per_km": round(r[18], 3) if r[18] else None,
                    "co2_per_km": round(r[19], 3) if r[19] else None,
                },
                "updated_at": r[20].isoformat() if r[20] else None,
            }
            for r in rows
        ]


async def get_flight_deviations(
    origin: str | None = None,
    destination: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    Return individual flight deviations from route baselines.

    Joins flights against route_performance to compute per-flight deviation.
    Useful for identifying specific outlier flights.
    """
    async with AsyncSessionLocal() as session:
        query = """
            SELECT
                f.flight_id, f.callsign, f.icao24, f.aircraft_type,
                f.origin_icao, f.destination_icao,
                f.first_seen, f.last_seen,
                EXTRACT(EPOCH FROM f.last_seen - f.first_seen) / 60 AS duration_min,
                f.total_fuel_kg, f.total_co2_kg, f.distance_km,
                rp.baseline_duration_min,
                rp.baseline_fuel_kg,
                rp.baseline_co2_kg,
                -- Per-flight deviations
                CASE WHEN rp.baseline_duration_min > 0
                     THEN (EXTRACT(EPOCH FROM f.last_seen - f.first_seen) / 60 - rp.baseline_duration_min)
                          / rp.baseline_duration_min * 100
                     ELSE NULL END AS duration_dev_pct,
                CASE WHEN rp.baseline_fuel_kg > 0
                     THEN (f.total_fuel_kg - rp.baseline_fuel_kg)
                          / rp.baseline_fuel_kg * 100
                     ELSE NULL END AS fuel_dev_pct,
                CASE WHEN rp.baseline_co2_kg > 0
                     THEN (f.total_co2_kg - rp.baseline_co2_kg)
                          / rp.baseline_co2_kg * 100
                     ELSE NULL END AS co2_dev_pct
            FROM flights f
            JOIN route_performance rp
                ON f.origin_icao = rp.origin_icao
                AND f.destination_icao = rp.destination_icao
            WHERE f.origin_icao IS NOT NULL
              AND f.destination_icao IS NOT NULL
              AND f.callsign LIKE 'SWR%'
        """
        params: dict = {"limit": limit}
        if origin:
            query += " AND f.origin_icao = :origin"
            params["origin"] = origin
        if destination:
            query += " AND f.destination_icao = :dest"
            params["dest"] = destination
        query += " ORDER BY f.first_seen DESC LIMIT :limit"

        result = await session.execute(text(query), params)
        rows = result.fetchall()

        return [
            {
                "flight_id": str(r[0]),
                "callsign": r[1],
                "icao24": r[2],
                "aircraft_type": r[3],
                "origin": r[4],
                "destination": r[5],
                "first_seen": r[6].isoformat() if r[6] else None,
                "last_seen": r[7].isoformat() if r[7] else None,
                "actual": {
                    "duration_min": round(r[8], 1) if r[8] else None,
                    "fuel_kg": round(r[9], 1) if r[9] else None,
                    "co2_kg": round(r[10], 1) if r[10] else None,
                    "distance_km": round(r[11], 1) if r[11] else None,
                },
                "baseline": {
                    "duration_min": round(r[12], 1) if r[12] else None,
                    "fuel_kg": round(r[13], 1) if r[13] else None,
                    "co2_kg": round(r[14], 1) if r[14] else None,
                },
                "deviation": {
                    "duration_pct": round(r[15], 2) if r[15] else None,
                    "fuel_pct": round(r[16], 2) if r[16] else None,
                    "co2_pct": round(r[17], 2) if r[17] else None,
                },
            }
            for r in rows
        ]
