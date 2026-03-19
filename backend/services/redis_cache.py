import json

import redis.asyncio as aioredis

from config import settings
from models.state_vector import StateVector

LIVE_FLIGHTS_KEY = "flights:live"


async def cache_flights(flights: list[StateVector]) -> None:
    """Store the latest state vectors in Redis (TTL = 2× poll interval)."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    async with r:
        payload = json.dumps([f.model_dump(mode="json") for f in flights], default=str)
        ttl = settings.poll_interval_seconds * 2
        await r.set(LIVE_FLIGHTS_KEY, payload, ex=ttl)


async def get_cached_flights() -> list[StateVector]:
    """Return the most recent state vectors from Redis, or [] if none."""
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    async with r:
        raw = await r.get(LIVE_FLIGHTS_KEY)
    if not raw:
        return []
    return [StateVector(**item) for item in json.loads(raw)]
