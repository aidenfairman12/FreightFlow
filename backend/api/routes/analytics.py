"""Freight analytics endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.corridor_performance import (
    compute_corridor_performance,
    get_corridor_performance_summary,
)
from services.freight_cost_model import compute_mode_cost_comparison

router = APIRouter()


@router.get("/corridor-performance")
async def get_corridor_perf(
    sort_by: str = Query("estimated_cost"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Corridor performance with efficiency scores."""
    routes = await get_corridor_performance_summary(sort_by=sort_by, limit=limit)
    return {"data": routes, "error": None, "meta": {"count": len(routes), "sort": sort_by}}


@router.get("/mode-comparison")
async def get_mode_comparison(
    year: int = Query(2022),
) -> dict[str, Any]:
    """Cost per ton-mile comparison across transport modes."""
    modes = await compute_mode_cost_comparison(year)
    return {"data": modes, "error": None, "meta": {"year": year, "count": len(modes)}}


@router.get("/commodity-summary")
async def get_commodity_summary(
    year: int = Query(2022),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Top commodities by volume for a given year."""
    result = await db.execute(text("""
        SELECT
            ff.sctg2, com.commodity_name,
            SUM(ff.tons_thousands) AS total_tons_k,
            SUM(ff.value_millions) AS total_value_m,
            SUM(ff.ton_miles_millions) AS total_tmiles_m
        FROM freight_flows ff
        LEFT JOIN commodities com ON ff.sctg2 = com.sctg2
        WHERE ff.year = :year
        GROUP BY ff.sctg2, com.commodity_name
        ORDER BY total_tons_k DESC NULLS LAST
        LIMIT :limit
    """), {"year": year, "limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"year": year, "count": len(rows)}}


@router.post("/corridor-performance/compute")
async def trigger_corridor_performance(
    year: int = Query(2022),
) -> dict[str, Any]:
    """Manually trigger corridor performance computation."""
    count = await compute_corridor_performance(year)
    return {"data": {"corridors_scored": count}, "error": None, "meta": {"triggered": True}}
