"""Phase 9: Scenario engine endpoints."""

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
            "name": "Fuel Price Spike (+20%)",
            "description": "What if jet fuel prices rise 20% from current levels?",
            "parameters": {"fuel_price_change_pct": 20},
        },
        {
            "name": "Fuel Price Drop (-15%)",
            "description": "What if jet fuel prices fall 15%?",
            "parameters": {"fuel_price_change_pct": -15},
        },
        {
            "name": "Carbon Price Surge (+50%)",
            "description": "EU ETS price increases 50% (regulatory tightening).",
            "parameters": {"carbon_price_change_pct": 50},
        },
        {
            "name": "Capacity Expansion (+10%)",
            "description": "SWISS adds 10% more ASK (new routes or frequencies).",
            "parameters": {"capacity_change_pct": 10},
        },
        {
            "name": "Load Factor Improvement (+5%)",
            "description": "Demand growth improves load factor by 5 percentage points.",
            "parameters": {"load_factor_change_pct": 5},
        },
        {
            "name": "Stagflation Scenario",
            "description": "Fuel +30%, carbon +20%, load factor -3% simultaneously.",
            "parameters": {
                "fuel_price_change_pct": 30,
                "carbon_price_change_pct": 20,
                "load_factor_change_pct": -3,
            },
        },
        {
            "name": "New Route: ZRH-BKK (3x weekly)",
            "description": "SWISS launches Zurich-Bangkok with 3 weekly frequencies.",
            "parameters": {"new_weekly_departures": 3, "capacity_change_pct": 2},
        },
        {
            "name": "CHF Strengthening (-5% EUR/CHF)",
            "description": "Swiss franc appreciates 5% against EUR (revenue pressure).",
            "parameters": {"fx_eur_chf_change_pct": -5},
        },
    ]
    return {"data": presets, "error": None, "meta": {"count": len(presets)}}
