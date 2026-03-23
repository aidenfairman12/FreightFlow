"""Freight economic data endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.economic_etl import get_latest_factors, get_factor_history, run_economic_etl

router = APIRouter()


@router.get("/latest")
async def get_latest_economic_factors() -> dict[str, Any]:
    """Return the most recent value for each tracked economic factor."""
    factors = await get_latest_factors()
    return {"data": factors, "error": None, "meta": {"count": len(factors)}}


@router.get("/history/{factor_name}")
async def get_factor_time_series(
    factor_name: str,
    days: int = Query(90, ge=1, le=730),
) -> dict[str, Any]:
    """Return time series for a specific economic factor."""
    history = await get_factor_history(factor_name, days)
    return {"data": history, "error": None, "meta": {"count": len(history), "factor": factor_name}}


@router.get("/unit-economics/current")
async def get_current_unit_economics(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return latest freight cost per ton-mile estimates."""
    result = await db.execute(text("""
        SELECT * FROM freight_unit_economics
        ORDER BY year DESC
        LIMIT 1
    """))
    row = result.mappings().first()
    if not row:
        return {"data": None, "error": "No unit economics data available yet", "meta": {}}
    return {"data": dict(row), "error": None, "meta": {}}


@router.get("/unit-economics/history")
async def get_unit_economics_history(
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return historical freight cost per ton-mile for trend charts."""
    result = await db.execute(text("""
        SELECT * FROM freight_unit_economics
        ORDER BY year DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/cost-breakdown")
async def get_cost_breakdown(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return latest freight cost breakdown by component for pie/bar charts."""
    result = await db.execute(text("""
        SELECT
            fuel_cost_per_tm,
            labor_cost_per_tm,
            equipment_cost_per_tm,
            insurance_cost_per_tm,
            tolls_fees_per_tm,
            other_cost_per_tm,
            total_cost_per_tm,
            year,
            scope
        FROM freight_unit_economics
        ORDER BY year DESC
        LIMIT 1
    """))
    row = result.mappings().first()
    if not row:
        return {"data": None, "error": "No cost breakdown data available", "meta": {}}

    breakdown = {
        "fuel": float(row["fuel_cost_per_tm"] or 0),
        "labor": float(row["labor_cost_per_tm"] or 0),
        "equipment": float(row["equipment_cost_per_tm"] or 0),
        "insurance": float(row["insurance_cost_per_tm"] or 0),
        "tolls_fees": float(row["tolls_fees_per_tm"] or 0),
        "other": float(row["other_cost_per_tm"] or 0),
    }
    return {
        "data": {
            "components": breakdown,
            "total_cost_per_tm": float(row["total_cost_per_tm"] or 0),
            "year": row["year"],
        },
        "error": None,
        "meta": {},
    }


@router.post("/refresh")
async def trigger_economic_etl() -> dict[str, Any]:
    """Manually trigger economic data refresh."""
    await run_economic_etl()
    factors = await get_latest_factors()
    return {"data": factors, "error": None, "meta": {"triggered": True}}
