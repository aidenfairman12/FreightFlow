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
    1. swiss_routes database (seed table + learned cache) — callsign-based, most reliable
    2. ICAO24 cache (enriched from OpenSky flights API) — only if callsign matches
    3. (None, None)

    The icao24 cache stores route data for a physical aircraft, but aircraft fly
    multiple legs with different callsigns. We only trust the cache when the
    callsign matches what was cached, to avoid serving stale route data from
    a previous leg.
    """
    # Primary source: swiss_routes (callsign-based, instant, most reliable)
    if callsign:
        origin, dest = swiss_routes.get_route(callsign)
        if origin and dest:
            return origin, dest

    # Secondary: icao24 cache, but only if callsign matches
    entry = _cache.get(icao24)
    if entry and (time.time() - entry["fetched_at"]) < entry["ttl"]:
        # Only trust cache if it was fetched for the same callsign
        if callsign and entry.get("callsign") == callsign:
            origin, dest = entry["origin"], entry["destination"]
            if origin and dest and origin != dest:
                return origin, dest

    # Partial swiss_routes data (e.g., origin from hub fallback, no destination)
    if callsign:
        origin, dest = swiss_routes.get_route(callsign)
        if origin:
            return origin, dest

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
                "origin": origin, "destination": dest, "callsign": callsign,
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
                api_callsign = (latest.get("callsign") or "").strip()

                # Validate: reject same origin and destination (data artifact)
                if origin and destination and origin == destination:
                    logger.debug("Ignoring same origin/dest %s for %s", origin, icao24)
                    origin, destination = None, None

                # Only learn route if the API flight's callsign matches the
                # current callsign. Otherwise, the API returned a previous leg
                # flown by this aircraft under a different flight number.
                callsign_matches = (
                    callsign and api_callsign and
                    api_callsign.upper().rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ") ==
                    callsign.strip().upper().rstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                )

                if callsign_matches and origin and destination:
                    swiss_routes.learn_route(callsign, origin, destination)

                # Cache with callsign tag so get_route can verify freshness
                _cache[icao24] = {
                    "origin": origin, "destination": destination,
                    "callsign": callsign,
                    "fetched_at": time.time(), "ttl": CACHE_TTL,
                }

                logger.debug("Route for %s (%s): %s -> %s (API cs: %s)",
                             icao24, callsign, origin, destination, api_callsign)
            else:
                # No flight records from API — use swiss_routes
                origin, dest = swiss_routes.get_route(callsign)
                _cache[icao24] = {
                    "origin": origin, "destination": dest, "callsign": callsign,
                    "fetched_at": time.time(), "ttl": CACHE_TTL,
                }
        elif resp.status_code == 429:
            logger.warning("Route lookup rate-limited for %s", icao24)
            origin, dest = swiss_routes.get_route(callsign)
            _cache[icao24] = {
                "origin": origin, "destination": dest, "callsign": callsign,
                "fetched_at": time.time(), "ttl": RETRY_TTL,
            }
        else:
            logger.warning("Route lookup for %s returned HTTP %d", icao24, resp.status_code)
            origin, dest = swiss_routes.get_route(callsign)
            _cache[icao24] = {
                "origin": origin, "destination": dest, "callsign": callsign,
                "fetched_at": time.time(), "ttl": RETRY_TTL,
            }
    except Exception:
        logger.exception("Route lookup failed for %s", icao24)
        origin, dest = swiss_routes.get_route(callsign)
        _cache[icao24] = {
            "origin": origin, "destination": dest, "callsign": callsign,
            "fetched_at": time.time(), "ttl": RETRY_TTL,
        }
    finally:
        _fetching.discard(icao24)
