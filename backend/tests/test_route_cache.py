"""Tests for services.route_cache — route resolution, caching, and learning.

Focuses on the bugs that caused incorrect origin/destination:
- Cross-leg learning (API returns previous leg under different callsign)
- Same origin/destination artifacts
- Stale icao24 cache serving wrong leg's route
"""

import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from services.route_cache import get_route, _fetch_route, _cache
from services.swiss_routes import _learned


@pytest.fixture(autouse=True)
def _clean_state():
    """Clear caches before/after each test."""
    saved_learned = _learned.copy()
    saved_cache = _cache.copy()
    _learned.clear()
    _cache.clear()
    yield
    _learned.clear()
    _learned.update(saved_learned)
    _cache.clear()
    _cache.update(saved_cache)


# ── get_route priority tests ────────────────────────────────────────────────


class TestGetRoutePriority:
    def test_swiss_routes_preferred_over_cache(self):
        """swiss_routes (callsign-based) should be checked before icao24 cache."""
        # Seed route: SWR8 = LSZH -> KJFK
        # Cache has stale data from previous leg
        _cache["abc123"] = {
            "origin": "EGLL", "destination": "LSZH",
            "callsign": "SWR317", "fetched_at": time.time(), "ttl": 14400,
        }
        origin, dest = get_route("abc123", "SWR8")
        assert origin == "LSZH"
        assert dest == "KJFK"

    def test_cache_only_trusted_when_callsign_matches(self):
        """Cache entry from different callsign should not be served."""
        _cache["abc123"] = {
            "origin": "EGLL", "destination": "LSZH",
            "callsign": "SWR317", "fetched_at": time.time(), "ttl": 14400,
        }
        # Unknown flight number, not in seed table — should NOT get cache data
        # because callsign doesn't match
        origin, dest = get_route("abc123", "SWR9999")
        # Should get hub fallback (LSZH, None), not the cached EGLL->LSZH
        assert origin == "LSZH"
        assert dest is None

    def test_cache_served_when_callsign_matches(self):
        """Cache entry should be served when callsign matches."""
        _cache["abc123"] = {
            "origin": "LSZH", "destination": "EGLL",
            "callsign": "SWR316", "fetched_at": time.time(), "ttl": 14400,
        }
        # SWR316 is in seed table too (LSZH->EGLL), but test that cache works
        origin, dest = get_route("abc123", "SWR316")
        assert origin == "LSZH"
        assert dest == "EGLL"

    def test_cache_rejects_same_origin_dest(self):
        """Even if callsign matches, same origin/dest should be rejected."""
        _cache["abc123"] = {
            "origin": "LSZH", "destination": "LSZH",
            "callsign": "SWR999", "fetched_at": time.time(), "ttl": 14400,
        }
        origin, dest = get_route("abc123", "SWR999")
        # Should fall through to hub fallback
        assert origin == "LSZH"
        assert dest is None

    def test_learned_route_takes_precedence(self):
        """Learned cache should override seed table."""
        _learned["SWR8"] = ["LSGG", "KJFK"]
        origin, dest = get_route("xyz789", "SWR8")
        assert origin == "LSGG"
        assert dest == "KJFK"

    def test_edw_callsign_returns_none_without_learned(self):
        """EDW callsigns have no seed table — fall to hub fallback."""
        origin, dest = get_route("def456", "EDW100")
        assert origin == "LSZH"
        assert dest is None

    def test_edw_learned_route(self):
        """EDW routes can be learned and retrieved."""
        _learned["EDW100"] = ["LSZH", "LGIR"]
        origin, dest = get_route("def456", "EDW100")
        assert origin == "LSZH"
        assert dest == "LGIR"

    def test_no_callsign_returns_none(self):
        origin, dest = get_route("abc123", None)
        assert origin is None
        assert dest is None


# ── _fetch_route learning tests ─────────────────────────────────────────────


def _mock_opensky_response(flights):
    """Create a mock httpx response with flight data."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = flights
    return resp


class TestFetchRouteLearning:
    @pytest.mark.asyncio
    async def test_learns_route_when_callsign_matches(self):
        """When API callsign matches current callsign, route should be learned."""
        flights = [{
            "firstSeen": 1000,
            "callsign": "SWR8  ",
            "estDepartureAirport": "LSZH",
            "estArrivalAirport": "KJFK",
        }]
        with patch("services.route_cache.can_call", return_value=True), \
             patch("services.route_cache.record_call"), \
             patch("services.route_cache.get_token", new_callable=AsyncMock, return_value="tok"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=_mock_opensky_response(flights))
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await _fetch_route("abc123", "SWR8")

        assert _learned.get("SWR8") == ["LSZH", "KJFK"]
        assert _cache["abc123"]["origin"] == "LSZH"
        assert _cache["abc123"]["destination"] == "KJFK"

    @pytest.mark.asyncio
    async def test_does_not_learn_when_callsign_differs(self):
        """When API returns a previous leg's callsign, should NOT learn."""
        # Aircraft just landed as SWR317 (LHR->ZRH), now showing SWR316
        # API returns the previous leg (SWR317)
        flights = [{
            "firstSeen": 1000,
            "callsign": "SWR317",
            "estDepartureAirport": "EGLL",
            "estArrivalAirport": "LSZH",
        }]
        with patch("services.route_cache.can_call", return_value=True), \
             patch("services.route_cache.record_call"), \
             patch("services.route_cache.get_token", new_callable=AsyncMock, return_value="tok"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=_mock_opensky_response(flights))
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await _fetch_route("abc123", "SWR316")

        # SWR316 should NOT be learned as EGLL->LSZH (that's SWR317's route)
        assert "SWR316" not in _learned
        # SWR317 should also not be learned (we didn't ask for it)
        assert "SWR317" not in _learned

    @pytest.mark.asyncio
    async def test_rejects_same_origin_destination(self):
        """Flights with same origin and destination should not be learned."""
        flights = [{
            "firstSeen": 1000,
            "callsign": "SWR53 ",
            "estDepartureAirport": "LSZH",
            "estArrivalAirport": "LSZH",
        }]
        with patch("services.route_cache.can_call", return_value=True), \
             patch("services.route_cache.record_call"), \
             patch("services.route_cache.get_token", new_callable=AsyncMock, return_value="tok"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=_mock_opensky_response(flights))
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await _fetch_route("abc123", "SWR53")

        assert "SWR53" not in _learned
        # Cache should store nulls (rejected data)
        assert _cache["abc123"]["origin"] is None
        assert _cache["abc123"]["destination"] is None

    @pytest.mark.asyncio
    async def test_cache_tagged_with_callsign(self):
        """Cache entries should be tagged with the callsign they were fetched for."""
        flights = [{
            "firstSeen": 1000,
            "callsign": "SWR8  ",
            "estDepartureAirport": "LSZH",
            "estArrivalAirport": "KJFK",
        }]
        with patch("services.route_cache.can_call", return_value=True), \
             patch("services.route_cache.record_call"), \
             patch("services.route_cache.get_token", new_callable=AsyncMock, return_value="tok"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=_mock_opensky_response(flights))
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await _fetch_route("abc123", "SWR8")

        assert _cache["abc123"]["callsign"] == "SWR8"

    @pytest.mark.asyncio
    async def test_callsign_suffix_matching(self):
        """SWR8A should match SWR8 (suffix stripped for comparison)."""
        flights = [{
            "firstSeen": 1000,
            "callsign": "SWR8A ",
            "estDepartureAirport": "LSZH",
            "estArrivalAirport": "KJFK",
        }]
        with patch("services.route_cache.can_call", return_value=True), \
             patch("services.route_cache.record_call"), \
             patch("services.route_cache.get_token", new_callable=AsyncMock, return_value="tok"), \
             patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=_mock_opensky_response(flights))
            ))
            mock_client.return_value.__aexit__ = AsyncMock(return_value=False)

            await _fetch_route("abc123", "SWR8")

        # Should still learn — SWR8A and SWR8 are the same flight
        assert _learned.get("SWR8") == ["LSZH", "KJFK"]


# ── Scenario: full leg turnaround ───────────────────────────────────────────


class TestTurnaroundScenario:
    """Simulate a real turnaround scenario that previously caused ZRH->ZRH."""

    def test_turnaround_does_not_pollute(self):
        """
        Aircraft flies SWR317 (LHR->ZRH), lands, then departs as SWR316 (ZRH->LHR).
        The icao24 cache from the SWR317 leg should NOT be served for SWR316.
        """
        # Step 1: SWR317 leg cached
        _cache["abc123"] = {
            "origin": "EGLL", "destination": "LSZH",
            "callsign": "SWR317", "fetched_at": time.time(), "ttl": 14400,
        }

        # Step 2: Aircraft now showing SWR316 callsign
        origin, dest = get_route("abc123", "SWR316")

        # Should get seed table data for SWR316 (LSZH->EGLL), NOT cache (EGLL->LSZH)
        assert origin == "LSZH"
        assert dest == "EGLL"

    def test_unknown_flight_not_polluted_by_previous_leg(self):
        """
        Aircraft flies SWR317 (LHR->ZRH), then shows unknown callsign SWR4999.
        Should NOT get SWR317's cached route.
        """
        _cache["abc123"] = {
            "origin": "EGLL", "destination": "LSZH",
            "callsign": "SWR317", "fetched_at": time.time(), "ttl": 14400,
        }
        origin, dest = get_route("abc123", "SWR4999")
        # Hub fallback, NOT the cached EGLL->LSZH
        assert origin == "LSZH"
        assert dest is None
