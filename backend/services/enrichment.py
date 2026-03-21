"""
Enrichment pipeline: augments raw StateVectors with aircraft type,
airline name, and (Phase 2) origin/destination airport.

Aircraft type is resolved via the OpenSky metadata API and cached
in-memory for the lifetime of the process (aircraft type never changes).
"""

import asyncio
import logging

import httpx

from services.opensky_auth import get_token

logger = logging.getLogger(__name__)

OPENSKY_METADATA_URL = "https://opensky-network.org/api/metadata/aircraft/icao/{icao24}"

# ICAO airline prefix -> human-readable name (expand as data comes in)
CALLSIGN_PREFIX_TO_AIRLINE: dict[str, str] = {
    "SWR": "SWISS",
    "EZS": "easyJet Switzerland",
    "EDW": "Edelweiss Air",
    "DLH": "Lufthansa",
    "AFR": "Air France",
    "BAW": "British Airways",
    "UAE": "Emirates",
    "THY": "Turkish Airlines",
    "SXS": "SunExpress",
    "RYR": "Ryanair",
}

# icao24 -> aircraft typecode (None = unknown, sentinel avoids re-fetching)
_type_cache: dict[str, str | None] = {}
_type_fetching: set[str] = set()
_semaphore = asyncio.Semaphore(3)


def lookup_airline(callsign: str | None) -> str | None:
    if not callsign:
        return None
    prefix = callsign[:3].upper()
    return CALLSIGN_PREFIX_TO_AIRLINE.get(prefix)


def get_aircraft_type(icao24: str) -> str | None:
    """Return cached aircraft type (or None if not yet resolved)."""
    return _type_cache.get(icao24)


def schedule_type_fetch(icao24: str) -> None:
    """Fire-and-forget metadata lookup if this ICAO24 hasn't been resolved yet."""
    if icao24 in _type_cache or icao24 in _type_fetching:
        return
    asyncio.create_task(_fetch_aircraft_type(icao24))


async def _fetch_aircraft_type(icao24: str) -> None:
    _type_fetching.add(icao24)
    try:
        async with _semaphore:
            token = await get_token()
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    OPENSKY_METADATA_URL.format(icao24=icao24),
                    headers={"Authorization": f"Bearer {token}"},
                )

        if resp.status_code == 200:
            data = resp.json()
            typecode = data.get("typecode") or data.get("manufacturerIcao")
            _type_cache[icao24] = typecode or None
            logger.debug("Aircraft type for %s: %s", icao24, typecode)
        elif resp.status_code == 404:
            _type_cache[icao24] = None  # unknown aircraft — don't retry
        else:
            logger.warning("Metadata lookup for %s returned HTTP %d", icao24, resp.status_code)
            # Don't cache on rate limit/error so we retry next encounter
    except Exception:
        logger.exception("Metadata lookup failed for %s", icao24)
    finally:
        _type_fetching.discard(icao24)
