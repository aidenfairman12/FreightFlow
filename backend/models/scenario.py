from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    parameters: dict  # e.g. {"fuel_price_change_pct": 20, "new_route": "ZRH-BKK"}
    base_period_start: datetime | None = None
    base_period_end: datetime | None = None


class Scenario(BaseModel):
    id: UUID | None = None
    name: str
    description: str | None = None
    parameters: dict
    results: dict | None = None
    base_period_start: datetime | None = None
    base_period_end: datetime | None = None
    status: str = "pending"
    created_at: datetime | None = None


class ScenarioResult(BaseModel):
    """Computed impact from a scenario run."""
    scenario_id: UUID
    baseline_cask: float | None = None
    scenario_cask: float | None = None
    delta_cask: float | None = None
    baseline_rask: float | None = None
    scenario_rask: float | None = None
    delta_rask: float | None = None
    baseline_fuel_cost: float | None = None
    scenario_fuel_cost: float | None = None
    impact_summary: str | None = None
    component_deltas: dict | None = None
