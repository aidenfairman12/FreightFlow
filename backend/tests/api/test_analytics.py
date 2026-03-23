"""Tests for /analytics API routes."""

import pytest
from unittest.mock import AsyncMock, patch

from tests.api.conftest import MockResult


class TestCommoditySummary:
    @pytest.mark.asyncio
    async def test_returns_data(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"sctg2": "35", "commodity_name": "Electronics", "total_tons_k": 500, "total_value_m": 12000, "total_tmiles_m": 300},
            {"sctg2": "01", "commodity_name": "Animals", "total_tons_k": 200, "total_value_m": 1000, "total_tmiles_m": 100},
        ])
        resp = await client.get("/analytics/commodity-summary?year=2022")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["meta"]["year"] == 2022


class TestModeComparison:
    @pytest.mark.asyncio
    async def test_returns_modes(self, client):
        with patch("api.routes.analytics.compute_mode_cost_comparison", new_callable=AsyncMock) as mock:
            mock.return_value = [
                {"mode_code": 1, "mode_name": "Truck", "cost_per_ton_mile": 0.12, "total_estimated_cost": 6000000},
                {"mode_code": 2, "mode_name": "Rail", "cost_per_ton_mile": 0.035, "total_estimated_cost": 1750000},
            ]
            resp = await client.get("/analytics/mode-comparison?year=2022")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 2
        assert data["meta"]["year"] == 2022


class TestCorridorPerformance:
    @pytest.mark.asyncio
    async def test_returns_summary(self, client):
        with patch("api.routes.analytics.get_corridor_performance_summary", new_callable=AsyncMock) as mock:
            mock.return_value = [
                {"name": "LA-Chicago", "estimated_cost": 5000000, "total_tons": 100000},
            ]
            resp = await client.get("/analytics/corridor-performance")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 1
