"""Tests for services.swiss_filter — SWISS + Edelweiss flight identification."""

from services.swiss_filter import is_swiss_flight, swiss_callsign_sql_filter


class TestIsSwissFlight:
    def test_swr_prefix_returns_true(self):
        assert is_swiss_flight("SWR8") is True

    def test_swr_with_suffix_returns_true(self):
        assert is_swiss_flight("SWR180A") is True

    def test_lowercase_returns_true(self):
        assert is_swiss_flight("swr22") is True

    def test_edelweiss_included_by_default(self):
        assert is_swiss_flight("EDW100") is True

    def test_edelweiss_lowercase(self):
        assert is_swiss_flight("edw55") is True

    def test_non_swiss_returns_false(self):
        assert is_swiss_flight("DLH123") is False

    def test_none_returns_false(self):
        assert is_swiss_flight(None) is False

    def test_empty_string_returns_false(self):
        assert is_swiss_flight("") is False


class TestSwissCallsignSqlFilter:
    def test_includes_both_prefixes(self):
        result = swiss_callsign_sql_filter()
        assert "SWR%" in result
        assert "EDW%" in result
