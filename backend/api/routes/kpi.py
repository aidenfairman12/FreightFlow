"""Freight KPI endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.freight_kpi_aggregator import compute_freight_kpis

router = APIRouter()


@router.get("/current")
async def get_current_kpis(
    scope: str = Query("national"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return the most recent freight KPIs."""
    result = await db.execute(text("""
        SELECT * FROM freight_kpis
        WHERE scope = :scope
        ORDER BY period_year DESC
        LIMIT 1
    """), {"scope": scope})
    row = result.mappings().first()
    if not row:
        return {"data": None, "error": "No KPI data available yet", "meta": {}}
    return {"data": dict(row), "error": None, "meta": {}}


@router.get("/history")
async def get_kpi_history(
    scope: str = Query("national"),
    limit: int = Query(20, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return historical freight KPIs for trend analysis."""
    result = await db.execute(text("""
        SELECT * FROM freight_kpis
        WHERE scope = :scope
        ORDER BY period_year DESC
        LIMIT :limit
    """), {"scope": scope, "limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/mode-share")
async def get_mode_share(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mode share breakdown over time (national scope)."""
    result = await db.execute(text("""
        SELECT
            period_year,
            truck_share_pct,
            rail_share_pct,
            air_share_pct,
            water_share_pct,
            multi_share_pct
        FROM freight_kpis
        WHERE scope = 'national'
        ORDER BY period_year ASC
    """))
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.post("/compute")
async def trigger_kpi_computation(
    year: int = Query(2022),
    scope: str = Query("national"),
) -> dict[str, Any]:
    """Manually trigger KPI computation for a specific year and scope."""
    result = await compute_freight_kpis(year, scope)
    if result:
        return {"data": result, "error": None, "meta": {"triggered": True}}
    return {"data": None, "error": "Insufficient data for KPI computation", "meta": {}}
