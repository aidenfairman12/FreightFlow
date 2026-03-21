from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OperationalKPI(BaseModel):
    id: UUID | None = None
    period_start: datetime
    period_end: datetime
    period_type: str  # 'weekly' or 'monthly'
    airline_code: str = "SWR"
    total_ask: float | None = None
    avg_block_hours_per_day: float | None = None
    total_block_hours: float | None = None
    unique_aircraft_count: int | None = None
    total_departures: int | None = None
    unique_routes: int | None = None
    avg_turnaround_min: float | None = None
    fuel_burn_per_ask: float | None = None
    co2_per_ask: float | None = None
    total_fuel_kg: float | None = None
    total_co2_kg: float | None = None
    estimated_load_factor: float | None = None


class KPISummary(BaseModel):
    """Lightweight summary for dashboard cards."""
    total_ask: float
    fleet_utilization_hours: float
    unique_aircraft: int
    total_departures: int
    unique_routes: int
    avg_turnaround_min: float
    fuel_per_ask: float
    period_label: str
