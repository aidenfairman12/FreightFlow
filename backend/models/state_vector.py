from datetime import datetime
from pydantic import BaseModel


class StateVector(BaseModel):
    icao24: str
    callsign: str | None
    origin_country: str | None
    latitude: float | None
    longitude: float | None
    baro_altitude: float | None
    on_ground: bool
    velocity: float | None
    heading: float | None
    vertical_rate: float | None
    geo_altitude: float | None
    squawk: str | None
    last_contact: datetime
    # Enrichment fields (populated during poll cycle)
    aircraft_type: str | None = None
    airline_name: str | None = None
    origin_airport: str | None = None
    destination_airport: str | None = None
    fuel_flow_kg_s: float | None = None
    co2_kg_s: float | None = None
