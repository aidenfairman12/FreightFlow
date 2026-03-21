from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.redis_cache import get_cached_flights

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
          AND callsign LIKE 'SWR%'
        ORDER BY icao24, time DESC
    """))
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows), "source": "database"}}


@router.get("/history")
async def get_flight_history(limit: int = 100) -> dict[str, Any]:
    """Return recent enriched flights from PostgreSQL."""
    # TODO Phase 2: SELECT * FROM flights ORDER BY first_seen DESC LIMIT $1
    return {"data": [], "error": None, "meta": {"count": 0}}
