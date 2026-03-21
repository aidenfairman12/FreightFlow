"""Tests for /kpi API routes."""

import pytest

from tests.api.conftest import MockResult


class TestCurrentKPIs:
    @pytest.mark.asyncio
    async def test_found(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"id": "abc", "airline_code": "SWR", "period_type": "weekly",
             "total_ask": 1000000, "total_departures": 500},
        ])
        resp = await client.get("/kpi/current")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] is not None
        assert data["error"] is None

    @pytest.mark.asyncio
    async def test_not_found(self, client, mock_db):
        mock_db.execute.return_value = MockResult([])
        resp = await client.get("/kpi/current")

        assert resp.status_code == 200
        data = resp.json()
        assert data["data"] is None
        assert "No KPI data" in data["error"]


class TestKPIHistory:
    @pytest.mark.asyncio
    async def test_returns_list(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"id": "1", "period_type": "weekly"},
            {"id": "2", "period_type": "weekly"},
            {"id": "3", "period_type": "weekly"},
        ])
        resp = await client.get("/kpi/history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 3


class TestFleetUtilization:
    @pytest.mark.asyncio
    async def test_returns_fleet(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"icao24": "aaa", "callsign": "SWR8", "block_hours": 5.2, "observations": 100},
            {"icao24": "bbb", "callsign": "SWR22", "block_hours": 3.1, "observations": 60},
        ])
        resp = await client.get("/kpi/fleet")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 2
        assert data["meta"]["hours"] == 24
