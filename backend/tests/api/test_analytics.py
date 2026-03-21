"""Tests for /analytics API routes."""

import pytest

from tests.api.conftest import MockResult


class TestFuelAnalytics:
    @pytest.mark.asyncio
    async def test_returns_data(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"icao24": "aaa", "callsign": "SWR8", "avg_fuel_kg_s": 1.2, "avg_co2_kg_s": 3.8, "samples": 100},
            {"icao24": "bbb", "callsign": "SWR22", "avg_fuel_kg_s": 1.0, "avg_co2_kg_s": 3.1, "samples": 80},
        ])
        resp = await client.get("/analytics/fuel")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2


class TestEmissions:
    @pytest.mark.asyncio
    async def test_returns_aggregates(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"aircraft_count": 5, "total_co2_kg_s": 10.0, "total_fuel_kg_s": 5.0},
        ])
        resp = await client.get("/analytics/emissions")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["aircraft_count"] == 5
        assert data["total_fuel_kg_s"] == 5.0


class TestNetwork:
    @pytest.mark.asyncio
    async def test_stub_returns_empty(self, client):
        resp = await client.get("/analytics/network")
        assert resp.status_code == 200
        assert resp.json()["data"] == []
