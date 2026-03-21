"""Tests for services.aircraft_data — aircraft specs, cruise mass, speed, load factors."""

from services.aircraft_data import (
    get_cruise_mass_kg,
    get_cruise_speed_kmh,
    get_load_factor,
    get_seat_count,
    get_aircraft_spec,
    AircraftSpec,
)


class TestGetCruiseMassKg:
    def test_known_type_a320(self):
        assert get_cruise_mass_kg("A320") == int(78_000 * 0.75)

    def test_known_type_b77w(self):
        assert get_cruise_mass_kg("B77W") == int(351_500 * 0.75)

    def test_unknown_type_returns_default(self):
        assert get_cruise_mass_kg("ZZZZ") == 65_000

    def test_none_returns_default(self):
        assert get_cruise_mass_kg(None) == 65_000

    def test_case_insensitive(self):
        assert get_cruise_mass_kg("a320") == get_cruise_mass_kg("A320")


class TestGetCruiseSpeedKmh:
    def test_a320_speed(self):
        assert get_cruise_speed_kmh("A320") == 828

    def test_unknown_speed(self):
        assert get_cruise_speed_kmh("ZZZZ") == 800

    def test_none_speed(self):
        assert get_cruise_speed_kmh(None) == 800


class TestGetLoadFactor:
    def test_regional(self):
        assert get_load_factor("E190") == 0.72

    def test_narrowbody(self):
        assert get_load_factor("A320") == 0.82

    def test_widebody(self):
        assert get_load_factor("B77W") == 0.87

    def test_unknown(self):
        assert get_load_factor("ZZZZ") == 0.82


class TestGetSeatCount:
    def test_known_type(self):
        assert get_seat_count("A321") == 219

    def test_none_returns_default(self):
        assert get_seat_count(None) == 170


class TestGetAircraftSpec:
    def test_known_type(self):
        spec = get_aircraft_spec("A320")
        assert isinstance(spec, AircraftSpec)
        assert spec.typecode == "A320"
        assert spec.category == "narrowbody"

    def test_none_returns_none(self):
        assert get_aircraft_spec(None) is None
