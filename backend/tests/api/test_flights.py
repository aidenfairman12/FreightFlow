"""Tests for /flights API routes."""

import pytest
from unittest.mock import AsyncMock, patch

from tests.api.conftest import MockResult


class TestLiveFlights:
    @pytest.mark.asyncio
    async def test_from_cache(self, client, sample_state_vector):
        with patch("api.routes.flights.get_cached_flights", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = [sample_state_vector]
            resp = await client.get("/flights/live")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["source"] == "cache"
        assert data["meta"]["count"] == 1

    @pytest.mark.asyncio
    async def test_cache_empty_falls_back_to_db(self, client, mock_db):
        with patch("api.routes.flights.get_cached_flights", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = []
            mock_db.execute.return_value = MockResult([
                {"icao24": "abc123", "callsign": "SWR8", "latitude": 47.4, "longitude": 8.5},
            ])
            resp = await client.get("/flights/live")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["source"] == "database"
        assert data["meta"]["count"] == 1

    @pytest.mark.asyncio
    async def test_both_empty(self, client, mock_db):
        with patch("api.routes.flights.get_cached_flights", new_callable=AsyncMock) as mock_cache:
            mock_cache.return_value = []
            mock_db.execute.return_value = MockResult([])
            resp = await client.get("/flights/live")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] == []
        assert data["meta"]["count"] == 0

    @pytest.mark.asyncio
    async def test_flight_history_stub(self, client):
        resp = await client.get("/flights/history")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
