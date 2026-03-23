"""Tests for /kpi API routes."""

import pytest

from tests.api.conftest import MockResult


class TestCurrentKPIs:
    @pytest.mark.asyncio
    async def test_found(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"id": "abc", "scope": "national", "period_year": 2022,
             "total_tons": 500000, "total_value_usd": 1e9,
             "truck_share_pct": 65.0, "rail_share_pct": 20.0},
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
            {"id": "1", "scope": "national", "period_year": 2022},
            {"id": "2", "scope": "national", "period_year": 2021},
            {"id": "3", "scope": "national", "period_year": 2020},
        ])
        resp = await client.get("/kpi/history")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 3


class TestModeShare:
    @pytest.mark.asyncio
    async def test_returns_mode_share(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"period_year": 2022, "truck_share_pct": 65.0, "rail_share_pct": 20.0,
             "air_share_pct": 0.5, "water_share_pct": 5.0, "multi_share_pct": 9.5},
        ])
        resp = await client.get("/kpi/mode-share")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 1
