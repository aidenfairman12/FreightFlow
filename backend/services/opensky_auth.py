"""
Shared OpenSky OAuth2 token manager.

Caches a single Bearer token and refreshes it when expired.
All services (state vectors, metadata, flights API) should use this
instead of acquiring their own tokens.
"""

import logging
import time

import httpx

from config import settings

logger = logging.getLogger(__name__)

OPENSKY_TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)

_cached_token: str | None = None
_token_expires_at: float = 0


async def get_token() -> str:
    """Return a valid Bearer token, refreshing if expired."""
    global _cached_token, _token_expires_at

    if _cached_token and time.time() < _token_expires_at:
        return _cached_token

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            OPENSKY_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.opensky_client_id,
                "client_secret": settings.opensky_client_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()

    _cached_token = data["access_token"]
    # Refresh 60s before expiry (tokens are typically 300s)
    expires_in = data.get("expires_in", 300)
    _token_expires_at = time.time() + expires_in - 60
    logger.debug("OpenSky token refreshed, expires in %ds", expires_in)
    return _cached_token
