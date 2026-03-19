from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class EnrichedFlight(BaseModel):
    flight_id: UUID | None = None
    icao24: str
    callsign: str | None
    aircraft_type: str | None
    airline_code: str | None
    airline_name: str | None
    origin_icao: str | None
    destination_icao: str | None
    first_seen: datetime | None
    last_seen: datetime | None
    distance_km: float | None
    total_fuel_kg: float | None
    total_co2_kg: float | None
    max_altitude: float | None
    avg_speed: float | None
