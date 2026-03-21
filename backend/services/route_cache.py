"""
In-memory route cache: maps icao24 -> (origin_airport, destination_airport).

Primary route resolution comes from swiss_routes module (static seed table +
persistent learned cache). The OpenSky flights API provides secondary
validation and feeds new routes back into the learning system.

When OpenSky returns route data for a completed flight, the callsign -> route
mapping is stored persistently via swiss_routes.learn_route(). This means
any given flight number only needs to be successfully looked up once — after
that, all future flights with the same callsign get instant route data.
"""

import asyncio
import logging
import time

import httpx

from services.opensky_auth import get_token
from services.opensky_credits import can_call, record_call
from services import swiss_routes

logger = logging.getLogger(__name__)

OPENSKY_FLIGHTS_URL = "https://opensky-network.org/api/flights/aircraft"

CACHE_TTL = 14400  # 4 hours (conserve API credits)
RETRY_TTL = 600    # 10 minutes after failure

_semaphore = asyncio.Semaphore(5)

# icao24 -> {"origin": str|None, "destination": str|None, "fetched_at": float, "ttl": int}
_cache: dict[str, dict] = {}
_fetching: set[str] = set()


def get_route(icao24: str, callsign: str | None = None) -> tuple[str | None, str | None]:
    """Return (origin, destination) using best available data.

    Priority:
    1. ICAO24 cache (enriched from OpenSky flights API)
    2. swiss_routes database (seed table + learned cache)
    3. (None, None)
    """
    # Check icao24-specific cache first (has validated API data)
    entry = _cache.get(icao24)
    if entry and (time.time() - entry["fetched_at"]) < entry["ttl"]:
        origin, dest = entry["origin"], entry["destination"]
        if origin and dest:
            return origin, dest

    # Primary source: swiss_routes (callsign-based, instant)
    if callsign:
        origin, dest = swiss_routes.get_route(callsign)
        if origin:
            return origin, dest

    # Fall back to icao24 cache even if only partial data
    if entry and (time.time() - entry["fetched_at"]) < entry["ttl"]:
        return entry["origin"], entry["destination"]

    return None, None


def schedule_fetch(icao24: str, callsign: str | None = None) -> None:
    """Fire-and-forget background route lookup via OpenSky flights API.

    The API result is cached by icao24 AND learned by callsign for
    future flights with the same flight number.
    """
    if icao24 in _fetching:
        return
    entry = _cache.get(icao24)
    if entry and (time.time() - entry["fetched_at"]) < entry["ttl"]:
        return

    asyncio.create_task(_fetch_route(icao24, callsign))


async def _fetch_route(icao24: str, callsign: str | None = None) -> None:
    _fetching.add(icao24)
    try:
        if not can_call():
            logger.debug("Skipping route lookup for %s — daily credit limit reached", icao24)
            # Fall back to swiss_routes only
            origin, dest = swiss_routes.get_route(callsign)
            _cache[icao24] = {
                "origin": origin, "destination": dest,
                "fetched_at": time.time(), "ttl": RETRY_TTL,
            }
            return
        async with _semaphore:
            token = await get_token()
            record_call()
            async with httpx.AsyncClient(timeout=15) as client:
                end = int(time.time())
                begin = end - 86400
                resp = await client.get(
                    OPENSKY_FLIGHTS_URL,
                    params={"icao24": icao24, "begin": begin, "end": end},
                    headers={"Authorization": f"Bearer {token}"},
                )

        if resp.status_code == 200:
            flights = resp.json()
            if flights:
                latest = max(flights, key=lambda f: f.get("firstSeen", 0))
                origin = latest.get("estDepartureAirport")
                destination = latest.get("estArrivalAirport")

                # For in-flight aircraft, API may return null arrival.
                # Fill from swiss_routes if we have it.
                if callsign and (not origin or not destination):
                    sr_origin, sr_dest = swiss_routes.get_route(callsign)
                    origin = origin or sr_origin
                    destination = destination or sr_dest

                _cache[icao24] = {
                    "origin": origin, "destination": destination,
                    "fetched_at": time.time(), "ttl": CACHE_TTL,
                }

                # Feed back to learning system (only if we have good data)
                if callsign and origin and destination:
                    swiss_routes.learn_route(callsign, origin, destination)

                logger.debug("Route for %s: %s -> %s", icao24, origin, destination)
            else:
                # No flight records from API — use swiss_routes
                origin, dest = swiss_routes.get_route(callsign)
                _cache[icao24] = {
                    "origin": origin, "destination": dest,
                    "fetched_at": time.time(), "ttl": CACHE_TTL,
                }
        elif resp.status_code == 429:
            logger.warning("Route lookup rate-limited for %s", icao24)
            origin, dest = swiss_routes.get_route(callsign)
            _cache[icao24] = {
                "origin": origin, "destination": dest,
                "fetched_at": time.time(), "ttl": RETRY_TTL,
            }
        else:
            logger.warning("Route lookup for %s returned HTTP %d", icao24, resp.status_code)
            origin, dest = swiss_routes.get_route(callsign)
            _cache[icao24] = {
                "origin": origin, "destination": dest,
                "fetched_at": time.time(), "ttl": RETRY_TTL,
            }
    except Exception:
        logger.exception("Route lookup failed for %s", icao24)
        origin, dest = swiss_routes.get_route(callsign)
        _cache[icao24] = {
            "origin": origin, "destination": dest,
            "fetched_at": time.time(), "ttl": RETRY_TTL,
        }
    finally:
        _fetching.discard(icao24)
