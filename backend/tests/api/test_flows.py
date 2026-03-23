"""Tests for /flows API routes."""

import pytest

from tests.api.conftest import MockResult


class TestQueryFlows:
    @pytest.mark.asyncio
    async def test_returns_flows(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"origin_zone_id": 61, "origin_name": "Los Angeles", "dest_zone_id": 171, "dest_name": "Chicago",
             "sctg2": "35", "commodity_name": "Electronics", "mode_code": 1, "mode_name": "Truck",
             "year": 2022, "tons_thousands": 100, "value_millions": 5000, "ton_miles_millions": 200},
        ])
        resp = await client.get("/flows/?year=2022")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 1

    @pytest.mark.asyncio
    async def test_with_filters(self, client, mock_db):
        mock_db.execute.return_value = MockResult([])
        resp = await client.get("/flows/?year=2022&commodity=35&mode=1")

        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestTopCorridors:
    @pytest.mark.asyncio
    async def test_returns_top(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"origin_zone_id": 61, "origin_name": "LA", "dest_zone_id": 171, "dest_name": "Chicago",
             "total_tons_k": 5000, "total_value_m": 100000, "total_tmiles_m": 10000},
        ])
        resp = await client.get("/flows/top-corridors?year=2022")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 1
        assert data["meta"]["year"] == 2022


class TestZones:
    @pytest.mark.asyncio
    async def test_returns_zones(self, client, mock_db):
        mock_db.execute.return_value = MockResult([
            {"zone_id": 61, "zone_name": "Los Angeles-Long Beach", "state_name": "CA",
             "latitude": 33.9, "longitude": -118.4, "zone_type": "metro"},
            {"zone_id": 171, "zone_name": "Chicago", "state_name": "IL",
             "latitude": 41.9, "longitude": -87.6, "zone_type": "metro"},
        ])
        resp = await client.get("/flows/zones")

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["count"] == 2
