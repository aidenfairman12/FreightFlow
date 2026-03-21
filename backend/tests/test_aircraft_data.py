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


class TestEdelweissOverrides:
    def test_edw_a320_seats(self):
        assert get_seat_count("A320", "EDW100") == 174

    def test_edw_a343_seats(self):
        assert get_seat_count("A343", "EDW55") == 314

    def test_edw_a359_seats(self):
        assert get_seat_count("A359", "EDW200") == 339

    def test_swr_a320_uses_swiss_spec(self):
        assert get_seat_count("A320", "SWR100") == 180

    def test_no_callsign_uses_swiss_spec(self):
        assert get_seat_count("A320") == 180

    def test_edw_unknown_type_falls_back_to_main(self):
        assert get_seat_count("B77W", "EDW10") == 320

    def test_edw_spec_returns_correct_object(self):
        spec = get_aircraft_spec("A359", "EDW200")
        assert spec.seats == 339
        assert spec.typecode == "A359"

    def test_edw_callsign_case_insensitive(self):
        assert get_seat_count("A320", "edw100") == 174
