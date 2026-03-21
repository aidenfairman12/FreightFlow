"""Tests for services.enrichment — airline lookup and aircraft type fetch."""

import pytest
import respx
import httpx

from services.enrichment import lookup_airline, _fetch_aircraft_type, _type_cache
from services.opensky_auth import OPENSKY_TOKEN_URL


class TestLookupAirline:
    def test_swr_returns_swiss(self):
        assert lookup_airline("SWR8") == "SWISS"

    def test_dlh_returns_lufthansa(self):
        assert lookup_airline("DLH456") == "Lufthansa"

    def test_unknown_prefix_returns_none(self):
        assert lookup_airline("XYZ99") is None

    def test_none_returns_none(self):
        assert lookup_airline(None) is None


class TestFetchAircraftType:
    @respx.mock
    @pytest.mark.asyncio
    async def test_success_caches_type(self):
        # Mock OpenSky token endpoint
        respx.post(OPENSKY_TOKEN_URL).mock(
            return_value=httpx.Response(200, json={
                "access_token": "test-token",
                "expires_in": 300,
            })
        )
        # Mock metadata endpoint
        respx.get("https://opensky-network.org/api/metadata/aircraft/icao/abc123").mock(
            return_value=httpx.Response(200, json={"typecode": "A320"})
        )

        await _fetch_aircraft_type("abc123")
        assert _type_cache["abc123"] == "A320"

    @respx.mock
    @pytest.mark.asyncio
    async def test_404_caches_none(self):
        respx.post(OPENSKY_TOKEN_URL).mock(
            return_value=httpx.Response(200, json={
                "access_token": "test-token",
                "expires_in": 300,
            })
        )
        respx.get("https://opensky-network.org/api/metadata/aircraft/icao/unknown1").mock(
            return_value=httpx.Response(404)
        )

        await _fetch_aircraft_type("unknown1")
        assert _type_cache["unknown1"] is None
