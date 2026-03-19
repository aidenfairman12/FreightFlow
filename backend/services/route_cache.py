"""
In-memory route cache: maps icao24 → (origin_airport, destination_airport).

On first encounter of an aircraft, schedules a fire-and-forget background
task that calls the OpenSky flights API to find the most recent flight record.
Results are cached for CACHE_TTL seconds to avoid hammering the API.
Failed / rate-limited lookups are cached for RETRY_TTL seconds before retry.
A semaphore limits concurrent lookups so we don't flood OpenSky on startup.
"""

import asyncio
import logging
import time

import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
OPENSKY_FLIGHTS_URL = "https://opensky-network.org/api/flights/aircraft"

CACHE_TTL = 7200   # 2 hours — routes don't change mid-flight
RETRY_TTL = 300    # 5 minutes — back-off after a failed/rate-limited lookup

_semaphore = asyncio.Semaphore(3)  # max 3 concurrent lookups

# icao24 -> {"origin": str|None, "destination": str|None, "fetched_at": float, "ttl": int}
_cache: dict[str, dict] = {}
_fetching: set[str] = set()


def get_route(icao24: str) -> tuple[str | None, str | None]:
    """Return cached (origin, destination) or (None, None) if not yet known."""
    entry = _cache.get(icao24)
    if entry and (time.time() - entry["fetched_at"]) < entry["ttl"]:
        return entry["origin"], entry["destination"]
    return None, None


def schedule_fetch(icao24: str) -> None:
    """Fire-and-forget a background route lookup if not already in-flight or freshly cached."""
    if icao24 in _fetching:
        return
    entry = _cache.get(icao24)
    if entry and (time.time() - entry["fetched_at"]) < entry["ttl"]:
        return  # still within TTL (success or retry cooldown)
    asyncio.create_task(_fetch_route(icao24))


async def _fetch_route(icao24: str) -> None:
    _fetching.add(icao24)
    try:
        async with _semaphore:
            async with httpx.AsyncClient(timeout=15) as client:
                token_resp = await client.post(
                    OPENSKY_TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": settings.opensky_client_id,
                        "client_secret": settings.opensky_client_secret,
                    },
                )
                token_resp.raise_for_status()
                token = token_resp.json()["access_token"]

                end = int(time.time())
                begin = end - 86400  # last 24 hours
                resp = await client.get(
                    OPENSKY_FLIGHTS_URL,
                    params={"icao24": icao24, "begin": begin, "end": end},
                    headers={"Authorization": f"Bearer {token}"},
                )

        if resp.status_code == 200:
            flights = resp.json()
            if flights:
                latest = max(flights, key=lambda f: f.get("lastSeen", 0))
                _cache[icao24] = {
                    "origin": latest.get("estDepartureAirport"),
                    "destination": latest.get("estArrivalAirport"),
                    "fetched_at": time.time(),
                    "ttl": CACHE_TTL,
                }
            else:
                _cache[icao24] = {"origin": None, "destination": None, "fetched_at": time.time(), "ttl": CACHE_TTL}
        else:
            logger.warning("Route lookup for %s returned HTTP %d", icao24, resp.status_code)
            # Cache the failure briefly so we don't hammer the API on every poll
            _cache[icao24] = {"origin": None, "destination": None, "fetched_at": time.time(), "ttl": RETRY_TTL}
    except Exception:
        logger.exception("Route lookup failed for %s", icao24)
        _cache[icao24] = {"origin": None, "destination": None, "fetched_at": time.time(), "ttl": RETRY_TTL}
    finally:
        _fetching.discard(icao24)
