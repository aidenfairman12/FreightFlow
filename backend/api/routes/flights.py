from typing import Any

from fastapi import APIRouter

from services.redis_cache import get_cached_flights

router = APIRouter()


@router.get("/live")
async def get_live_flights() -> dict[str, Any]:
    """Return current state vectors from the Redis cache."""
    flights = await get_cached_flights()
    return {"data": [f.model_dump(mode="json") for f in flights], "error": None, "meta": {"count": len(flights)}}


@router.get("/history")
async def get_flight_history(limit: int = 100) -> dict[str, Any]:
    """Return recent enriched flights from PostgreSQL."""
    # TODO Phase 2: SELECT * FROM flights ORDER BY first_seen DESC LIMIT $1
    return {"data": [], "error": None, "meta": {"count": 0}}
