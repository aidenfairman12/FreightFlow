"""
Static aircraft reference data: seat counts, MTOW, range, cruise speed.

Used by the KPI aggregator to compute ASK (Available Seat Kilometers),
the fuel model for mass-dependent burn estimation, and the unit economics
module for cost estimation.

Sources:
- SWISS seat counts & cabin configs: https://www.swiss.com/ch/en/discover/fleet
- Edelweiss seat counts & cabin configs: https://www.edelweissair.com/en/fly/our-fleet
- Fleet counts: Lufthansa Group 2025 Annual Report (files/t011_group_fleet_*.xlsx)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AircraftSpec:
    typecode: str
    name: str
    seats: int              # typical 2-class config
    mtow_kg: int            # max takeoff weight
    range_km: int           # typical range
    category: str           # 'narrowbody', 'widebody', 'regional'
    cruise_speed_kmh: int   # typical cruise speed (km/h), from manufacturer data


# SWISS + Edelweiss fleet (116 aircraft per LH Group 2025 report) + common Swiss airspace types
# Seat counts for SWISS types: swiss.com/ch/en/discover/fleet
AIRCRAFT_SPECS: dict[str, AircraftSpec] = {
    # SWISS long-haul fleet (seat counts from swiss.com/ch/en/discover/fleet)
    "A333": AircraftSpec("A333", "Airbus A330-300", 236, 242_000, 11_750, "widebody", 871),       # 8F+45J+183Y
    "A343": AircraftSpec("A343", "Airbus A340-300", 215, 276_500, 13_700, "widebody", 871),       # 8F+42J+21W+144Y
    "A359": AircraftSpec("A359", "Airbus A350-900", 242, 280_000, 15_000, "widebody", 903),       # 3F+45J+38W+156Y
    "B77W": AircraftSpec("B77W", "Boeing 777-300ER", 320, 351_500, 13_650, "widebody", 892),      # 8F+62J+24W+226Y
    # SWISS short-haul fleet (seat counts from swiss.com/ch/en/discover/fleet/airbus-shorthaul.html)
    # NOTE: Short-haul seat counts use the published "passenger seats" total from swiss.com.
    # Class breakdowns (J+Y) on these types are less reliable — swiss.com seat maps sometimes
    # don't match published totals, likely due to variable cabin configurations across the fleet.
    "BCS1": AircraftSpec("BCS1", "Airbus A220-100", 125, 63_100, 5_460, "narrowbody", 830),
    "BCS3": AircraftSpec("BCS3", "Airbus A220-300", 145, 69_900, 6_297, "narrowbody", 830),
    "A320": AircraftSpec("A320", "Airbus A320-200", 180, 78_000, 6_150, "narrowbody", 828),
    "A20N": AircraftSpec("A20N", "Airbus A320neo", 180, 79_000, 6_300, "narrowbody", 833),
    "A321": AircraftSpec("A321", "Airbus A321-200", 219, 93_500, 5_950, "narrowbody", 828),
    "A21N": AircraftSpec("A21N", "Airbus A321neo", 215, 97_000, 7_400, "narrowbody", 828),
    # Other common types in Swiss airspace
    "B738": AircraftSpec("B738", "Boeing 737-800", 189, 79_016, 5_436, "narrowbody", 842),
    "B38M": AircraftSpec("B38M", "Boeing 737 MAX 8", 189, 82_191, 6_570, "narrowbody", 839),
    "B789": AircraftSpec("B789", "Boeing 787-9", 290, 254_000, 14_140, "widebody", 903),
    "B788": AircraftSpec("B788", "Boeing 787-8", 242, 228_000, 13_530, "widebody", 903),
    "E190": AircraftSpec("E190", "Embraer E190", 100, 51_800, 4_537, "regional", 829),
    "E195": AircraftSpec("E195", "Embraer E195", 120, 52_290, 4_260, "regional", 829),
    "E295": AircraftSpec("E295", "Embraer E195-E2", 132, 61_500, 4_815, "regional", 833),
    "CRJ9": AircraftSpec("CRJ9", "Bombardier CRJ-900", 90, 38_330, 2_956, "regional", 830),
    "AT76": AircraftSpec("AT76", "ATR 72-600", 72, 23_000, 1_528, "regional", 510),
    "DH8D": AircraftSpec("DH8D", "Dash 8-400", 78, 30_481, 2_040, "regional", 556),
}

# Edelweiss Air fleet (seat counts from edelweissair.com/en/fly/our-fleet)
# Edelweiss is a leisure carrier (SWISS subsidiary), so configs are denser than SWISS mainline.
# NOTE: Edelweiss A340-300 has two configs — HB-JMC (300 seats: 29J+76W+195Y) vs all others
# (314 seats: 27J+76W+211Y). We use the 314-seat majority config because we cannot currently
# distinguish by registration (OpenSky API does not provide registration in state vectors).
# If per-registration lookup becomes available, HB-JMC should be handled separately.
EDELWEISS_SPECS: dict[str, AircraftSpec] = {
    "A320": AircraftSpec("A320", "Airbus A320-200", 174, 78_000, 6_150, "narrowbody", 828),
    "A343": AircraftSpec("A343", "Airbus A340-300", 314, 276_500, 13_700, "widebody", 871),       # 27J+76W+211Y (majority config)
    "A359": AircraftSpec("A359", "Airbus A350-900", 339, 280_000, 15_000, "widebody", 903),       # 30J+63W+246Y
}

# Fallback defaults (generic narrowbody assumptions)
DEFAULT_SEATS = 170
DEFAULT_CRUISE_MASS_KG = 65_000
DEFAULT_CRUISE_SPEED_KMH = 800

# Load factor by aircraft category (IATA/Lufthansa Group 2023 data)
# Short-haul European routes have lower LF than long-haul
LOAD_FACTOR_BY_CATEGORY = {
    "regional": 0.72,    # thinner routes, smaller markets
    "narrowbody": 0.82,  # European short/medium-haul
    "widebody": 0.87,    # intercontinental long-haul
}
DEFAULT_LOAD_FACTOR = 0.82


def _is_edelweiss(callsign: str | None) -> bool:
    """Check if a callsign belongs to Edelweiss Air."""
    return bool(callsign) and callsign[:3].upper() == "EDW"


def _resolve_spec(aircraft_type: str | None, callsign: str | None = None) -> AircraftSpec | None:
    """Resolve aircraft spec, checking Edelweiss overrides first if callsign is EDW."""
    if not aircraft_type:
        return None
    key = aircraft_type.upper()
    if _is_edelweiss(callsign):
        spec = EDELWEISS_SPECS.get(key)
        if spec:
            return spec
    return AIRCRAFT_SPECS.get(key)


def get_cruise_mass_kg(aircraft_type: str | None, callsign: str | None = None) -> int:
    """
    Estimate typical mid-cruise mass for an aircraft type.

    Uses ~75% of MTOW as a reasonable mid-flight estimate:
    aircraft are lighter than MTOW (fuel burned, not max payload)
    but heavier than OEW (still carrying passengers + remaining fuel).
    """
    spec = _resolve_spec(aircraft_type, callsign)
    if not spec:
        return DEFAULT_CRUISE_MASS_KG
    return int(spec.mtow_kg * 0.75)


def get_cruise_speed_kmh(aircraft_type: str | None, callsign: str | None = None) -> int:
    """Return typical cruise speed (km/h) for an aircraft type."""
    spec = _resolve_spec(aircraft_type, callsign)
    return spec.cruise_speed_kmh if spec else DEFAULT_CRUISE_SPEED_KMH


def get_load_factor(aircraft_type: str | None, callsign: str | None = None) -> float:
    """Return estimated load factor based on aircraft category."""
    spec = _resolve_spec(aircraft_type, callsign)
    if not spec:
        return DEFAULT_LOAD_FACTOR
    return LOAD_FACTOR_BY_CATEGORY.get(spec.category, DEFAULT_LOAD_FACTOR)


def get_seat_count(aircraft_type: str | None, callsign: str | None = None) -> int:
    """Return typical seat count for an aircraft type."""
    spec = _resolve_spec(aircraft_type, callsign)
    return spec.seats if spec else DEFAULT_SEATS


def get_aircraft_spec(aircraft_type: str | None, callsign: str | None = None) -> AircraftSpec | None:
    """Return full spec for an aircraft type, or None if unknown."""
    return _resolve_spec(aircraft_type, callsign)


# Major Swiss airports with coordinates (for distance estimation)
SWISS_AIRPORTS: dict[str, tuple[float, float]] = {
    "LSZH": (47.4647, 8.5492),   # Zurich
    "LSGG": (46.2381, 6.1089),   # Geneva
    "LFSB": (47.5896, 7.5299),   # Basel (EuroAirport)
    "LSZB": (46.9141, 7.4975),   # Bern
    "LSZA": (46.0040, 8.9106),   # Lugano
    "LSZR": (47.4850, 9.5608),   # St. Gallen-Altenrhein
}
