"""
Aggregates state_vectors into completed flights in the flights table.

A flight is considered complete when an icao24 disappears from polls
(landed or no longer reporting) after being tracked for >2 minutes.

Only SWISS (SWR) flights are in state_vectors since ingestion filters globally.
Runs periodically (e.g. every 5 minutes) to detect completed flights.
"""

import logging
from math import radians, sin, cos, asin, sqrt

from sqlalchemy import text

from db.session import AsyncSessionLocal
from services import swiss_routes

logger = logging.getLogger(__name__)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in km."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


async def aggregate_completed_flights() -> int:
    """
    Find icao24s that have state_vectors in the last 30min but none in the
    last 3min (likely departed Swiss airspace), and summarize them into flights.

    Returns count of newly aggregated flights.
    """
    async with AsyncSessionLocal() as session:
        # Step 1: Identify completed flights and compute summaries
        # Uses actual time deltas between consecutive samples instead of
        # assuming a fixed poll interval (which would undercount in collect mode).
        summaries_result = await session.execute(text("""
            WITH recently_active AS (
                SELECT DISTINCT icao24
                FROM state_vectors
                WHERE time > NOW() - INTERVAL '30 minutes'
                  AND time < NOW() - INTERVAL '3 minutes'
                  AND icao24 NOT IN (
                      SELECT DISTINCT icao24
                      FROM state_vectors
                      WHERE time > NOW() - INTERVAL '3 minutes'
                  )
            ),
            with_deltas AS (
                SELECT sv.*,
                    LEAST(
                        COALESCE(
                            EXTRACT(EPOCH FROM
                                sv.time - LAG(sv.time) OVER (
                                    PARTITION BY sv.icao24 ORDER BY sv.time
                                )
                            ),
                            10
                        ),
                        60  -- cap at 60s to prevent data gaps from inflating totals
                    ) AS dt_seconds
                FROM state_vectors sv
                JOIN recently_active ra ON sv.icao24 = ra.icao24
                WHERE sv.time > NOW() - INTERVAL '30 minutes'
            )
            SELECT
                icao24,
                MAX(callsign) AS callsign,
                MIN(time) AS first_seen,
                MAX(time) AS last_seen,
                MAX(baro_altitude) AS max_altitude,
                AVG(velocity) FILTER (WHERE on_ground = false) AS avg_speed,
                SUM(fuel_flow_kg_s * dt_seconds)
                    FILTER (WHERE fuel_flow_kg_s IS NOT NULL) AS total_fuel_kg,
                SUM(co2_kg_s * dt_seconds)
                    FILTER (WHERE co2_kg_s IS NOT NULL) AS total_co2_kg,
                (ARRAY_AGG(latitude ORDER BY time ASC))[1] AS first_lat,
                (ARRAY_AGG(longitude ORDER BY time ASC))[1] AS first_lon,
                (ARRAY_AGG(latitude ORDER BY time DESC))[1] AS last_lat,
                (ARRAY_AGG(longitude ORDER BY time DESC))[1] AS last_lon
            FROM with_deltas
            GROUP BY icao24
            HAVING COUNT(*) >= 12
               AND EXTRACT(EPOCH FROM MAX(time) - MIN(time)) > 120
        """))
        summaries = summaries_result.fetchall()

        if not summaries:
            return 0

        # Filter out already-aggregated flights
        existing_result = await session.execute(text("""
            SELECT icao24 FROM flights
            WHERE first_seen > NOW() - INTERVAL '35 minutes'
        """))
        existing_icao24s = {r[0] for r in existing_result.fetchall()}

        new_flights = [s for s in summaries if s[0] not in existing_icao24s]
        if not new_flights:
            return 0

        # Step 2: Insert flights and enrich with route + distance
        count = 0
        for s in new_flights:
            icao24, callsign = s[0], s[1]
            first_seen, last_seen = s[2], s[3]
            max_altitude, avg_speed = s[4], s[5]
            total_fuel_kg, total_co2_kg = s[6], s[7]
            first_lat, first_lon = s[8], s[9]
            last_lat, last_lon = s[10], s[11]

            # Compute distance from first/last observed positions
            distance_km = None
            if all(v is not None for v in [first_lat, first_lon, last_lat, last_lon]):
                distance_km = _haversine_km(first_lat, first_lon, last_lat, last_lon)

            origin, dest = swiss_routes.get_route(callsign)

            result = await session.execute(text("""
                INSERT INTO flights (icao24, callsign, first_seen, last_seen,
                                     max_altitude, avg_speed, total_fuel_kg, total_co2_kg,
                                     distance_km, origin_icao, destination_icao)
                VALUES (:icao24, :callsign, :first_seen, :last_seen,
                        :max_alt, :avg_spd, :fuel, :co2,
                        :dist, :origin, :dest)
                RETURNING flight_id
            """), {
                "icao24": icao24, "callsign": callsign,
                "first_seen": first_seen, "last_seen": last_seen,
                "max_alt": max_altitude, "avg_spd": avg_speed,
                "fuel": total_fuel_kg, "co2": total_co2_kg,
                "dist": distance_km, "origin": origin, "dest": dest,
            })
            result.fetchone()
            count += 1

            # Update route_analytics rolling averages
            if origin and dest:
                duration_min = None
                if first_seen and last_seen:
                    duration_min = (last_seen - first_seen).total_seconds() / 60
                await session.execute(
                    text("""
                        INSERT INTO route_analytics
                            (origin_icao, destination_icao, flight_count,
                             avg_fuel_kg, avg_duration_min, avg_co2_kg,
                             avg_distance_km, last_updated)
                        VALUES (:origin, :dest, 1,
                                :fuel, :dur, :co2, :dist, NOW())
                        ON CONFLICT (origin_icao, destination_icao) DO UPDATE SET
                            flight_count = route_analytics.flight_count + 1,
                            avg_fuel_kg = (COALESCE(route_analytics.avg_fuel_kg, 0) * route_analytics.flight_count + COALESCE(:fuel, 0))
                                          / (route_analytics.flight_count + 1),
                            avg_duration_min = (COALESCE(route_analytics.avg_duration_min, 0) * route_analytics.flight_count + COALESCE(:dur, 0))
                                               / (route_analytics.flight_count + 1),
                            avg_co2_kg = (COALESCE(route_analytics.avg_co2_kg, 0) * route_analytics.flight_count + COALESCE(:co2, 0))
                                         / (route_analytics.flight_count + 1),
                            avg_distance_km = (COALESCE(route_analytics.avg_distance_km, 0) * route_analytics.flight_count + COALESCE(:dist, 0))
                                              / (route_analytics.flight_count + 1),
                            last_updated = NOW()
                    """),
                    {"origin": origin, "dest": dest, "fuel": total_fuel_kg,
                     "dur": duration_min, "co2": total_co2_kg, "dist": distance_km},
                )

        await session.commit()

        if count > 0:
            logger.info("Aggregated %d completed flights", count)
        return count
