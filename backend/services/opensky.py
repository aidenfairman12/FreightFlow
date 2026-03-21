"""
OpenSky Network API client.

OAuth2 client credentials flow — acquire a token then poll state vectors
for SWISS International Air Lines flights worldwide.

Fetches global state vectors and filters to SWR callsign prefix (SWISS).
OpenSky state vector field order: https://opensky-network.org/apidoc/rest.html
"""

import logging

import httpx
from datetime import datetime

from config import settings
from models.state_vector import StateVector
from services.opensky_auth import get_token
from services.opensky_credits import can_call, record_call
from services.swiss_filter import is_swiss_flight

logger = logging.getLogger(__name__)

OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"


async def validate_credentials() -> bool:
    """Test OpenSky credentials at startup. Returns True if valid."""
    if not settings.opensky_client_id or not settings.opensky_client_secret:
        logger.error(
            "OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET are not set. "
            "OpenSky polling will be disabled. "
            "Set them in .env (see .env.example)."
        )
        return False
    try:
        token = await get_token()
        logger.info("OpenSky credentials validated successfully")
        return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.error(
                "OpenSky credentials are invalid (HTTP 401). "
                "Check OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in .env."
            )
        else:
            logger.error("OpenSky token endpoint returned HTTP %d", e.response.status_code)
        return False
    except httpx.ConnectError:
        logger.warning(
            "Cannot reach OpenSky auth server — network may be unavailable. "
            "OpenSky polling will start but may fail until connectivity is restored."
        )
        return True  # allow startup, polling will retry
    except Exception:
        logger.exception("Unexpected error validating OpenSky credentials")
        return False


async def fetch_swiss_states() -> list[StateVector]:
    """Poll OpenSky for all SWISS (SWR) flights worldwide."""
    if not can_call():
        logger.warning("Skipping state poll — daily credit limit reached")
        return []
    token = await get_token()
    record_call()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            OPENSKY_STATES_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()

    all_states = [_parse_state_vector(sv) for sv in (data.get("states") or [])]
    swiss_flights = [sv for sv in all_states if is_swiss_flight(sv.callsign)]
    logger.debug("Global states: %d, SWISS flights: %d", len(all_states), len(swiss_flights))
    return swiss_flights


def _parse_state_vector(sv: list) -> StateVector:
    """Map the OpenSky state vector array to a typed model.

    Field indices from OpenSky REST docs:
    0  icao24          4  last_contact    8  on_ground
    1  callsign        5  longitude       9  velocity
    2  origin_country  6  latitude       10  heading
    3  time_position   7  baro_altitude  11  vertical_rate
                                         13  geo_altitude
                                         14  squawk
    """
    return StateVector(
        icao24=sv[0],
        callsign=sv[1].strip() if sv[1] else None,
        origin_country=sv[2],
        last_contact=datetime.fromtimestamp(sv[4]),
        longitude=sv[5],
        latitude=sv[6],
        baro_altitude=sv[7],
        on_ground=sv[8],
        velocity=sv[9],
        heading=sv[10],
        vertical_rate=sv[11],
        geo_altitude=sv[13],
        squawk=sv[14],
    )
