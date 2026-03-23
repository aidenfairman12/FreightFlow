from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScenarioCreate(BaseModel):
    name: str
    description: str | None = None
    parameters: dict
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
    baseline_cost_per_tm: float | None = None
    scenario_cost_per_tm: float | None = None
    delta_cost_per_tm: float | None = None
    baseline_total_cost: float | None = None
    scenario_total_cost: float | None = None
    delta_total_cost: float | None = None
    impact_summary: str | None = None
    component_deltas: dict | None = None
