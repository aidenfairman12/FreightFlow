"""
Phase 5: Operational KPI aggregation for SWISS flights.

Computes weekly/monthly metrics from state_vectors:
- ASK (Available Seat Kilometers)
- Fleet utilization (block hours per aircraft per day)
- Route frequency
- Turnaround time
- Fuel burn per ASK
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services.aircraft_data import get_seat_count, get_cruise_speed_kmh, get_load_factor
from services.swiss_filter import swiss_callsign_sql_filter

logger = logging.getLogger(__name__)


async def compute_kpis(
    period_start: datetime,
    period_end: datetime,
    period_type: str = "weekly",
) -> dict | None:
    """
    Aggregate SWISS operational KPIs for a given period.

    Returns a dict suitable for INSERT into operational_kpis, or None
    if insufficient data.
    """
    swiss_filter = swiss_callsign_sql_filter()
    period_days = (period_end - period_start).days or 1

    async with AsyncSessionLocal() as session:
        # 1. Fleet utilization: distinct aircraft, total airborne time
        # Uses actual time deltas between consecutive samples instead of
        # assuming a fixed poll interval.
        util_result = await session.execute(text(f"""
            WITH with_deltas AS (
                SELECT
                    icao24, on_ground,
                    LEAST(
                        COALESCE(
                            EXTRACT(EPOCH FROM
                                time - LAG(time) OVER (
                                    PARTITION BY icao24 ORDER BY time
                                )
                            ),
                            10
                        ),
                        60  -- cap at 60s to prevent data gaps from inflating totals
                    ) AS dt_seconds
                FROM state_vectors
                WHERE time >= :start AND time < :end
                  AND {swiss_filter}
            )
            SELECT
                COUNT(DISTINCT icao24) AS unique_aircraft,
                COALESCE(SUM(dt_seconds) FILTER (WHERE on_ground = false), 0) / 3600.0
                    AS total_block_hours,
                COUNT(*) AS total_observations
            FROM with_deltas
        """), {"start": period_start, "end": period_end})
        util = util_result.mappings().one()

        if util["total_observations"] == 0:
            logger.info("No SWISS data for period %s - %s", period_start, period_end)
            return None

        unique_aircraft = util["unique_aircraft"]
        total_block_hours = float(util["total_block_hours"] or 0)
        avg_block_per_day = total_block_hours / (unique_aircraft * period_days) if unique_aircraft else 0

        # 2. Route frequency and ASK estimation
        route_result = await session.execute(text(f"""
            WITH flight_segments AS (
                SELECT
                    icao24,
                    callsign,
                    MIN(time) AS seg_start,
                    MAX(time) AS seg_end,
                    -- Distance proxy: sum of consecutive position deltas
                    COUNT(*) AS obs_count,
                    MAX(baro_altitude) AS max_alt
                FROM state_vectors
                WHERE time >= :start AND time < :end
                  AND {swiss_filter}
                  AND on_ground = false
                GROUP BY icao24, callsign,
                         -- Segment by gaps > 5 min between observations
                         time_bucket('5 minutes', time)
            )
            SELECT
                COUNT(DISTINCT (icao24, callsign, seg_start::date)) AS departures,
                COUNT(DISTINCT callsign) AS unique_routes
            FROM flight_segments
            WHERE obs_count >= 6  -- at least 1 minute of tracking
        """), {"start": period_start, "end": period_end})
        routes = route_result.mappings().one()
        total_departures = routes["departures"]
        unique_routes = routes["unique_routes"]

        # 3. ASK estimation: for each tracked SWISS flight, seats × estimated distance
        ask_result = await session.execute(text(f"""
            WITH aircraft_types AS (
                SELECT DISTINCT icao24,
                    MODE() WITHIN GROUP (ORDER BY callsign) AS callsign
                FROM state_vectors
                WHERE time >= :start AND time < :end
                  AND {swiss_filter}
                GROUP BY icao24
            ),
            aircraft_with_type AS (
                SELECT at.icao24, at.callsign, ar.aircraft_type
                FROM aircraft_types at
                LEFT JOIN aircraft_registry ar ON at.icao24 = ar.icao24
            )
            SELECT icao24, callsign, aircraft_type
            FROM aircraft_with_type
        """), {"start": period_start, "end": period_end})

        # Compute ASK from aircraft types and per-type cruise speed
        total_ask = 0.0
        weighted_load_factor = 0.0
        aircraft_count = 0
        for row in ask_result.mappings():
            ac_type = row["aircraft_type"]
            seats = get_seat_count(ac_type)
            cruise_speed = get_cruise_speed_kmh(ac_type)
            # Each aircraft's contribution: seats × (block_hours × speed)
            aircraft_block_hours = total_block_hours / unique_aircraft if unique_aircraft else 0
            distance_km = aircraft_block_hours * cruise_speed
            total_ask += seats * distance_km
            # Accumulate weighted load factor by category
            weighted_load_factor += get_load_factor(ac_type)
            aircraft_count += 1

        # 4. Fuel totals (using actual time deltas between samples)
        fuel_result = await session.execute(text(f"""
            WITH with_deltas AS (
                SELECT
                    fuel_flow_kg_s, co2_kg_s, on_ground,
                    LEAST(
                        COALESCE(
                            EXTRACT(EPOCH FROM
                                time - LAG(time) OVER (
                                    PARTITION BY icao24 ORDER BY time
                                )
                            ),
                            10
                        ),
                        60
                    ) AS dt_seconds
                FROM state_vectors
                WHERE time >= :start AND time < :end
                  AND {swiss_filter}
                  AND on_ground = false
                  AND fuel_flow_kg_s IS NOT NULL
            )
            SELECT
                COALESCE(SUM(fuel_flow_kg_s * dt_seconds), 0) AS total_fuel_kg,
                COALESCE(SUM(co2_kg_s * dt_seconds), 0) AS total_co2_kg
            FROM with_deltas
        """), {"start": period_start, "end": period_end})
        fuel = fuel_result.mappings().one()
        total_fuel_kg = float(fuel["total_fuel_kg"])
        total_co2_kg = float(fuel["total_co2_kg"])

        # 5. Turnaround time: time between last airborne and next airborne for same icao24
        turnaround_result = await session.execute(text(f"""
            WITH ground_periods AS (
                SELECT
                    icao24,
                    time,
                    on_ground,
                    LAG(on_ground) OVER (PARTITION BY icao24 ORDER BY time) AS prev_on_ground,
                    LAG(time) OVER (PARTITION BY icao24 ORDER BY time) AS prev_time
                FROM state_vectors
                WHERE time >= :start AND time < :end
                  AND {swiss_filter}
            ),
            transitions AS (
                SELECT
                    icao24,
                    prev_time AS landed_at,
                    time AS departed_at,
                    EXTRACT(EPOCH FROM time - prev_time) / 60 AS turnaround_min
                FROM ground_periods
                WHERE prev_on_ground = true AND on_ground = false
                  AND EXTRACT(EPOCH FROM time - prev_time) BETWEEN 600 AND 14400
                  -- Between 10 min and 4 hours (realistic turnaround)
            )
            SELECT AVG(turnaround_min) AS avg_turnaround_min
            FROM transitions
        """), {"start": period_start, "end": period_end})
        ta = turnaround_result.mappings().one()
        avg_turnaround = float(ta["avg_turnaround_min"]) if ta["avg_turnaround_min"] else None

        fuel_per_ask = (total_fuel_kg / total_ask * 1000) if total_ask > 0 else None  # g per ASK
        co2_per_ask = (total_co2_kg / total_ask * 1000) if total_ask > 0 else None

        # Fleet-weighted load factor based on aircraft categories observed
        estimated_lf = (weighted_load_factor / aircraft_count) if aircraft_count else 0.82

        kpi = {
            "period_start": period_start,
            "period_end": period_end,
            "period_type": period_type,
            "airline_code": "SWR",
            "total_ask": total_ask,
            "avg_block_hours_per_day": avg_block_per_day,
            "total_block_hours": total_block_hours,
            "unique_aircraft_count": unique_aircraft,
            "total_departures": total_departures,
            "unique_routes": unique_routes,
            "avg_turnaround_min": avg_turnaround,
            "fuel_burn_per_ask": fuel_per_ask,
            "co2_per_ask": co2_per_ask,
            "total_fuel_kg": total_fuel_kg,
            "total_co2_kg": total_co2_kg,
            "estimated_load_factor": estimated_lf,
        }

        # Upsert into operational_kpis
        await session.execute(text("""
            INSERT INTO operational_kpis (
                period_start, period_end, period_type, airline_code,
                total_ask, avg_block_hours_per_day, total_block_hours,
                unique_aircraft_count, total_departures, unique_routes,
                avg_turnaround_min, fuel_burn_per_ask, co2_per_ask,
                total_fuel_kg, total_co2_kg, estimated_load_factor
            ) VALUES (
                :period_start, :period_end, :period_type, :airline_code,
                :total_ask, :avg_block_hours_per_day, :total_block_hours,
                :unique_aircraft_count, :total_departures, :unique_routes,
                :avg_turnaround_min, :fuel_burn_per_ask, :co2_per_ask,
                :total_fuel_kg, :total_co2_kg, :estimated_load_factor
            )
            ON CONFLICT (period_start, period_type, airline_code)
            DO UPDATE SET
                total_ask = EXCLUDED.total_ask,
                avg_block_hours_per_day = EXCLUDED.avg_block_hours_per_day,
                total_block_hours = EXCLUDED.total_block_hours,
                unique_aircraft_count = EXCLUDED.unique_aircraft_count,
                total_departures = EXCLUDED.total_departures,
                unique_routes = EXCLUDED.unique_routes,
                avg_turnaround_min = EXCLUDED.avg_turnaround_min,
                fuel_burn_per_ask = EXCLUDED.fuel_burn_per_ask,
                co2_per_ask = EXCLUDED.co2_per_ask,
                total_fuel_kg = EXCLUDED.total_fuel_kg,
                total_co2_kg = EXCLUDED.total_co2_kg,
                estimated_load_factor = EXCLUDED.estimated_load_factor,
                created_at = NOW()
        """), kpi)
        await session.commit()

        logger.info("KPIs computed for %s (%s): ASK=%.0f, block_hrs=%.1f, departures=%d",
                     period_type, period_start.date(), total_ask, total_block_hours, total_departures)
        return kpi


async def compute_current_week_kpis() -> dict | None:
    """Compute KPIs for the current ISO week (Monday-Sunday)."""
    now = datetime.utcnow()
    # ISO weekday: Monday=1, Sunday=7
    start = now - timedelta(days=now.weekday(), hours=now.hour, minutes=now.minute, seconds=now.second)
    return await compute_kpis(start, now, "weekly")


async def compute_last_month_kpis() -> dict | None:
    """Compute KPIs for the previous calendar month."""
    now = datetime.utcnow()
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_of_month
    last_month_start = (first_of_month - timedelta(days=1)).replace(day=1)
    return await compute_kpis(last_month_start, last_month_end, "monthly")
