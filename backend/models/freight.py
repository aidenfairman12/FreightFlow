from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FafZone(BaseModel):
    zone_id: int
    zone_name: str
    state_fips: str | None = None
    state_name: str | None = None
    zone_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class Commodity(BaseModel):
    sctg2: str
    commodity_name: str
    commodity_group: str | None = None


class FreightFlow(BaseModel):
    id: UUID | None = None
    origin_zone_id: int
    dest_zone_id: int
    sctg2: str
    mode_code: int
    mode_name: str
    year: int
    data_type: str = "historical"
    tons_thousands: float | None = None
    value_millions: float | None = None
    ton_miles_millions: float | None = None


class Corridor(BaseModel):
    corridor_id: UUID | None = None
    name: str
    description: str | None = None
    origin_zones: list[int]
    dest_zones: list[int]
    origin_lat: float | None = None
    origin_lon: float | None = None
    dest_lat: float | None = None
    dest_lon: float | None = None


class CorridorPerformance(BaseModel):
    corridor_id: UUID
    year: int
    sctg2: str | None = None
    total_tons: float | None = None
    total_value_usd: float | None = None
    total_ton_miles: float | None = None
    mode_breakdown: dict | None = None
    avg_value_per_ton: float | None = None
    estimated_cost: float | None = None
    cost_per_ton: float | None = None


class FreightKPI(BaseModel):
    id: UUID | None = None
    period_year: int
    scope: str = "national"
    total_tons: float | None = None
    total_value_usd: float | None = None
    total_ton_miles: float | None = None
    truck_share_pct: float | None = None
    rail_share_pct: float | None = None
    air_share_pct: float | None = None
    water_share_pct: float | None = None
    multi_share_pct: float | None = None
    avg_cost_per_ton_mile: float | None = None
    total_estimated_cost: float | None = None
    value_per_ton: float | None = None
    ton_miles_per_ton: float | None = None


class FreightUnitEconomics(BaseModel):
    id: UUID | None = None
    year: int
    scope: str = "national"
    fuel_cost_per_tm: float | None = None
    labor_cost_per_tm: float | None = None
    equipment_cost_per_tm: float | None = None
    insurance_cost_per_tm: float | None = None
    tolls_fees_per_tm: float | None = None
    other_cost_per_tm: float | None = None
    total_cost_per_tm: float | None = None
    revenue_per_tm: float | None = None
    margin_per_tm: float | None = None
