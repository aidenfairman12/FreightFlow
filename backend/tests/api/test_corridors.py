"""Tests for /corridors API routes."""

import pytest
from unittest.mock import AsyncMock, patch

from tests.api.conftest import MockResult


class TestListCorridors:
    @pytest.mark.asyncio
    async def test_returns_corridors(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"corridor_id": "abc-123", "name": "LA → Chicago", "description": "Pacific imports to Midwest",
             "origin_zones": [61], "dest_zones": [171],
             "origin_lat": 33.9, "origin_lon": -118.4, "dest_lat": 41.9, "dest_lon": -87.6,
             "year": 2022, "total_tons": 100000, "total_value_usd": 5e9,
             "total_ton_miles": 200000, "mode_breakdown": None,
             "estimated_cost": 5000000, "cost_per_ton": 50.0},
        ])
        resp = await client.get("/corridors/")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 1
        assert data["data"][0]["name"] == "LA → Chicago"

    @pytest.mark.asyncio
    async def test_empty(self, client, mock_db):
        mock_db.execute.return_value = MockResult([])
        resp = await client.get("/corridors/")

        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestCorridorFlows:
    @pytest.mark.asyncio
    async def test_returns_flows(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"sctg2": "35", "commodity_name": "Electronics", "mode_code": 1, "mode_name": "Truck",
             "total_tons_k": 50, "total_value_m": 3000, "total_tmiles_m": 100},
        ])
        resp = await client.get("/corridors/00000000-0000-0000-0000-000000000001/flows?year=2022")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["data"]) == 1


class TestCorridorModes:
    @pytest.mark.asyncio
    async def test_returns_cost_data(self, client):
        with patch("api.routes.corridors.estimate_corridor_cost", new_callable=AsyncMock) as mock:
            mock.return_value = {
                "corridor_id": "abc",
                "year": 2022,
                "total_estimated_cost": 5000000,
                "modes": [{"mode_code": 1, "mode_name": "Truck", "cost_per_ton_mile": 0.12}],
            }
            resp = await client.get("/corridors/00000000-0000-0000-0000-000000000001/modes?year=2022")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["total_estimated_cost"] == 5000000
