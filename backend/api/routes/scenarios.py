"""Freight scenario engine endpoints."""

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.scenario import ScenarioCreate
from services.scenario_engine import run_scenario

router = APIRouter()


@router.post("/")
async def create_scenario(
    body: ScenarioCreate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create and execute a what-if scenario."""
    # Insert scenario record
    result = await db.execute(text("""
        INSERT INTO scenarios (name, description, parameters, base_period_start, base_period_end, status)
        VALUES (:name, :desc, :params, :bps, :bpe, 'running')
        RETURNING id
    """), {
        "name": body.name,
        "desc": body.description,
        "params": json.dumps(body.parameters),
        "bps": body.base_period_start,
        "bpe": body.base_period_end,
    })
    row = result.one()
    scenario_id = row[0]
    await db.commit()

    # Run scenario computation
    results = await run_scenario(
        scenario_id=scenario_id,
        parameters=body.parameters,
        base_period_start=body.base_period_start,
        base_period_end=body.base_period_end,
    )

    return {"data": results, "error": None, "meta": {"scenario_id": str(scenario_id)}}


@router.get("/")
async def list_scenarios(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all scenarios, most recent first."""
    result = await db.execute(text("""
        SELECT id, name, description, parameters, status, created_at
        FROM scenarios
        ORDER BY created_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get a specific scenario with its results."""
    result = await db.execute(text("""
        SELECT * FROM scenarios WHERE id = :id
    """), {"id": scenario_id})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"data": dict(row), "error": None, "meta": {}}


@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Delete a scenario."""
    result = await db.execute(text("""
        DELETE FROM scenarios WHERE id = :id RETURNING id
    """), {"id": scenario_id})
    row = result.first()
    await db.commit()
    if not row:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return {"data": {"deleted": str(scenario_id)}, "error": None, "meta": {}}


@router.get("/presets/list")
async def get_scenario_presets() -> dict[str, Any]:
    """Return predefined scenario templates."""
    presets = [
        {
            "name": "Diesel Price Spike (+30%)",
            "description": "What if diesel prices rise 30%? Impacts truck costs most severely.",
            "parameters": {"diesel_price_change_pct": 30},
        },
        {
            "name": "Port Congestion Crisis",
            "description": "Major port congestion adds 5 days delay, shifting cargo to truck.",
            "parameters": {"port_congestion_days": 5},
        },
        {
            "name": "Rail Capacity Expansion (+20%)",
            "description": "New rail infrastructure increases capacity 20%.",
            "parameters": {"rail_capacity_change_pct": 20},
        },
        {
            "name": "Truck Driver Shortage (-15%)",
            "description": "Driver shortage reduces trucking capacity 15%, rates surge.",
            "parameters": {"truck_driver_shortage_pct": 15},
        },
        {
            "name": "Mode Shift to Rail (10%)",
            "description": "Policy incentives shift 10% of truck volume to rail.",
            "parameters": {"mode_shift_to_rail_pct": 10},
        },
        {
            "name": "Carbon Tax ($0.02/ton-mile)",
            "description": "New carbon tax applied per ton-mile, hitting trucks hardest.",
            "parameters": {"carbon_tax_per_ton_mile": 0.02},
        },
        {
            "name": "Supply Chain Disruption",
            "description": "Diesel +20%, port +3 days delay, demand -5% simultaneously.",
            "parameters": {
                "diesel_price_change_pct": 20,
                "port_congestion_days": 3,
                "demand_change_pct": -5,
            },
        },
    ]
    return {"data": presets, "error": None, "meta": {"count": len(presets)}}
