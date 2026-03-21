from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.redis_cache import get_cached_flights
from services import route_cache
from services.enrichment import get_aircraft_type, lookup_airline
from services.fuel_model import estimate_for_sv

router = APIRouter()


@router.get("/live")
async def get_live_flights(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return current state vectors from Redis cache, falling back to DB."""
    flights = await get_cached_flights()
    if flights:
        return {"data": [f.model_dump(mode="json") for f in flights], "error": None, "meta": {"count": len(flights), "source": "cache"}}

    # Fallback: query DB directly (works in collect mode when Redis isn't populated)
    result = await db.execute(text("""
        SELECT DISTINCT ON (icao24)
            icao24, callsign, latitude, longitude,
            baro_altitude, on_ground, velocity, heading, vertical_rate,
            fuel_flow_kg_s, co2_kg_s
        FROM state_vectors
        WHERE time > NOW() - INTERVAL '2 minutes'
          AND (callsign LIKE 'SWR%' OR callsign LIKE 'EDW%')
        ORDER BY icao24, time DESC
    """))
    rows = []
    for r in result.mappings():
        row = dict(r)
        # Enrich with route, aircraft type, and airline — same as _poll_opensky()
        origin, destination = route_cache.get_route(row["icao24"], row.get("callsign"))
        aircraft_type = get_aircraft_type(row["icao24"])
        row["aircraft_type"] = aircraft_type
        row["airline_name"] = lookup_airline(row.get("callsign"))
        row["origin_airport"] = origin
        row["destination_airport"] = destination
        rows.append(row)
    return {"data": rows, "error": None, "meta": {"count": len(rows), "source": "database"}}


@router.get("/history")
async def get_flight_history(limit: int = 100) -> dict[str, Any]:
    """Return recent enriched flights from PostgreSQL."""
    # TODO Phase 2: SELECT * FROM flights ORDER BY first_seen DESC LIMIT $1
    return {"data": [], "error": None, "meta": {"count": 0}}
