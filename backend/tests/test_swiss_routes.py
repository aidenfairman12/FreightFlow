"""Tests for services.swiss_routes — route resolution, flight number parsing."""

import pytest

from services.swiss_routes import parse_flight_number, get_route, _learned, learn_route


@pytest.fixture(autouse=True)
def _clean_learned_cache():
    """Save and restore the learned routes cache between tests."""
    saved = _learned.copy()
    yield
    _learned.clear()
    _learned.update(saved)


class TestParseFlightNumber:
    def test_simple_number(self):
        assert parse_flight_number("SWR8") == 8

    def test_with_letter_suffix(self):
        assert parse_flight_number("SWR180A") == 180

    def test_lowercase(self):
        assert parse_flight_number("swr22") == 22

    def test_non_swr_returns_none(self):
        assert parse_flight_number("DLH100") is None

    def test_none_returns_none(self):
        assert parse_flight_number(None) is None


class TestGetRoute:
    def test_seed_route_swr8(self):
        origin, dest = get_route("SWR8")
        assert origin == "LSZH"
        assert dest == "KJFK"

    def test_learned_takes_precedence(self):
        _learned["SWR8"] = ["LSGG", "KJFK"]
        origin, dest = get_route("SWR8")
        assert origin == "LSGG"
        assert dest == "KJFK"

    def test_hub_fallback_zurich(self):
        # Flight number < 2000, not in seed → LSZH hub
        origin, dest = get_route("SWR1999")
        assert origin == "LSZH"
        assert dest is None

    def test_hub_fallback_geneva(self):
        # 2000 <= flight number < 3000 → LSGG hub
        origin, dest = get_route("SWR2500")
        assert origin == "LSGG"
        assert dest is None

    def test_non_swr_returns_none(self):
        origin, dest = get_route("DLH100")
        assert origin is None
        assert dest is None
