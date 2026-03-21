"""Tests for services.swiss_filter — SWISS flight identification."""

from services.swiss_filter import is_swiss_flight, swiss_callsign_sql_filter


class TestIsSwissFlight:
    def test_swr_prefix_returns_true(self):
        assert is_swiss_flight("SWR8") is True

    def test_swr_with_suffix_returns_true(self):
        assert is_swiss_flight("SWR180A") is True

    def test_lowercase_returns_true(self):
        assert is_swiss_flight("swr22") is True

    def test_non_swiss_returns_false(self):
        assert is_swiss_flight("DLH123") is False

    def test_none_returns_false(self):
        assert is_swiss_flight(None) is False

    def test_empty_string_returns_false(self):
        assert is_swiss_flight("") is False

    def test_edelweiss_excluded_by_default(self):
        assert is_swiss_flight("EDW100") is False

    def test_edelweiss_included_with_flag(self):
        assert is_swiss_flight("EDW100", include_edelweiss=True) is True


class TestSwissCallsignSqlFilter:
    def test_without_edelweiss(self):
        assert swiss_callsign_sql_filter() == "(callsign LIKE 'SWR%')"

    def test_with_edelweiss(self):
        result = swiss_callsign_sql_filter(include_edelweiss=True)
        assert result == "(callsign LIKE 'SWR%' OR callsign LIKE 'EDW%')"
