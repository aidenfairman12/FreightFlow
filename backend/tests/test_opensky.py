"""Tests for services.opensky — state vector parsing, fetch, credential validation."""

import pytest
import respx
import httpx

from services.opensky import _parse_state_vector, fetch_swiss_states, validate_credentials, OPENSKY_STATES_URL
from services.opensky_auth import OPENSKY_TOKEN_URL
from models.state_vector import StateVector


class TestParseStateVector:
    def test_parse_basic(self, sample_state_vector_array):
        sv = _parse_state_vector(sample_state_vector_array)
        assert isinstance(sv, StateVector)
        assert sv.icao24 == "abc123"
        assert sv.latitude == 47.4647
        assert sv.baro_altitude == 10668.0
        assert sv.on_ground is False

    def test_strips_callsign_whitespace(self, sample_state_vector_array):
        sv = _parse_state_vector(sample_state_vector_array)
        assert sv.callsign == "SWR8"

    def test_none_callsign(self, sample_state_vector_array):
        sample_state_vector_array[1] = None
        sv = _parse_state_vector(sample_state_vector_array)
        assert sv.callsign is None

    def test_none_altitude(self, sample_state_vector_array):
        sample_state_vector_array[7] = None
        sv = _parse_state_vector(sample_state_vector_array)
        assert sv.baro_altitude is None


class TestFetchSwissStates:
    @respx.mock
    @pytest.mark.asyncio
    async def test_filters_to_swiss_only(self):
        respx.post(OPENSKY_TOKEN_URL).mock(
            return_value=httpx.Response(200, json={
                "access_token": "tok", "expires_in": 300,
            })
        )
        respx.get(OPENSKY_STATES_URL).mock(
            return_value=httpx.Response(200, json={"states": [
                # SWR flight
                ["aaa", "SWR8  ", "CH", None, 1700000000, 8.5, 47.4, 10000.0, False, 250.0, 90.0, 0.5, None, 10500.0, "1000", None, None],
                # Lufthansa flight
                ["bbb", "DLH100", "DE", None, 1700000000, 8.5, 47.4, 10000.0, False, 250.0, 90.0, 0.5, None, 10500.0, "1000", None, None],
                # Edelweiss (not included by default)
                ["ccc", "EDW50 ", "CH", None, 1700000000, 8.5, 47.4, 10000.0, False, 250.0, 90.0, 0.5, None, 10500.0, "1000", None, None],
            ]})
        )

        result = await fetch_swiss_states()
        assert len(result) == 1
        assert result[0].callsign == "SWR8"

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_states(self):
        respx.post(OPENSKY_TOKEN_URL).mock(
            return_value=httpx.Response(200, json={
                "access_token": "tok", "expires_in": 300,
            })
        )
        respx.get(OPENSKY_STATES_URL).mock(
            return_value=httpx.Response(200, json={"states": None})
        )

        result = await fetch_swiss_states()
        assert result == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_http_error_raises(self):
        respx.post(OPENSKY_TOKEN_URL).mock(
            return_value=httpx.Response(200, json={
                "access_token": "tok", "expires_in": 300,
            })
        )
        respx.get(OPENSKY_STATES_URL).mock(
            return_value=httpx.Response(500)
        )

        with pytest.raises(httpx.HTTPStatusError):
            await fetch_swiss_states()


class TestValidateCredentials:
    @pytest.mark.asyncio
    async def test_no_credentials_returns_false(self, monkeypatch):
        from config import settings
        monkeypatch.setattr(settings, "opensky_client_id", "")
        monkeypatch.setattr(settings, "opensky_client_secret", "")
        result = await validate_credentials()
        assert result is False
