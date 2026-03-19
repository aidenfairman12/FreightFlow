"""
OpenSky Network API client.

OAuth2 client credentials flow — acquire a token then poll state vectors
for Swiss airspace every `poll_interval_seconds`.

Swiss bounding box: lamin=45.8, lamax=47.9, lomin=5.9, lomax=10.6
OpenSky state vector field order: https://opensky-network.org/apidoc/rest.html
"""

import httpx
from datetime import datetime

from config import settings
from models.state_vector import StateVector

OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
OPENSKY_STATES_URL = "https://opensky-network.org/api/states/all"

SWISS_BBOX = {
    "lamin": 45.8,
    "lamax": 47.9,
    "lomin": 5.9,
    "lomax": 10.6,
}


async def fetch_access_token(client: httpx.AsyncClient) -> str:
    """Exchange client credentials for a Bearer token."""
    response = await client.post(
        OPENSKY_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": settings.opensky_client_id,
            "client_secret": settings.opensky_client_secret,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]


async def fetch_swiss_states() -> list[StateVector]:
    """Poll OpenSky for all aircraft currently in Swiss airspace."""
    async with httpx.AsyncClient(timeout=15) as client:
        token = await fetch_access_token(client)
        response = await client.get(
            OPENSKY_STATES_URL,
            params=SWISS_BBOX,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        data = response.json()

    return [_parse_state_vector(sv) for sv in (data.get("states") or [])]


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
