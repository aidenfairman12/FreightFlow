"""Phase 6: Economic data endpoints."""

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
    """Return latest CASK/RASK estimates."""
    result = await db.execute(text("""
        SELECT * FROM unit_economics
        WHERE airline_code = 'SWR'
        ORDER BY period_start DESC
        LIMIT 1
    """))
    row = result.mappings().first()
    if not row:
        return {"data": None, "error": "No unit economics data available yet", "meta": {}}
    return {"data": dict(row), "error": None, "meta": {}}


@router.get("/unit-economics/history")
async def get_unit_economics_history(
    limit: int = Query(52, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return historical CASK/RASK for trend charts."""
    result = await db.execute(text("""
        SELECT * FROM unit_economics
        WHERE airline_code = 'SWR'
        ORDER BY period_start DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/cask-breakdown")
async def get_cask_breakdown(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return latest CASK broken down by component for pie/bar charts."""
    result = await db.execute(text("""
        SELECT
            fuel_cost_per_ask,
            carbon_cost_per_ask,
            nav_charges_per_ask,
            airport_cost_per_ask,
            crew_cost_per_ask,
            other_cost_per_ask,
            total_cask,
            period_start,
            period_type
        FROM unit_economics
        WHERE airline_code = 'SWR'
        ORDER BY period_start DESC
        LIMIT 1
    """))
    row = result.mappings().first()
    if not row:
        return {"data": None, "error": "No CASK data available", "meta": {}}

    breakdown = {
        "fuel": float(row["fuel_cost_per_ask"] or 0),
        "carbon": float(row["carbon_cost_per_ask"] or 0),
        "navigation": float(row["nav_charges_per_ask"] or 0),
        "airport": float(row["airport_cost_per_ask"] or 0),
        "crew": float(row["crew_cost_per_ask"] or 0),
        "other": float(row["other_cost_per_ask"] or 0),
    }
    return {
        "data": {
            "components": breakdown,
            "total_cask": float(row["total_cask"] or 0),
            "period": row["period_start"].isoformat() if row["period_start"] else None,
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
