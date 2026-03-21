"""Tests for services.flight_aggregator — haversine distance calculation."""

import pytest

from services.flight_aggregator import _haversine_km


class TestHaversineKm:
    def test_zurich_to_london(self):
        # LSZH (47.4647, 8.5492) -> EGLL (51.4706, -0.4619)
        dist = _haversine_km(47.4647, 8.5492, 51.4706, -0.4619)
        assert abs(dist - 773) < 30

    def test_same_point_is_zero(self):
        dist = _haversine_km(47.0, 8.0, 47.0, 8.0)
        assert dist == 0.0

    def test_zurich_to_new_york(self):
        # LSZH -> JFK (40.6413, -73.7781)
        dist = _haversine_km(47.4647, 8.5492, 40.6413, -73.7781)
        assert abs(dist - 6320) < 50

    def test_antipodal_points(self):
        dist = _haversine_km(0, 0, 0, 180)
        assert abs(dist - 20015) < 50
