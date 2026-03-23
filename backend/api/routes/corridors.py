"""Corridor API endpoints."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.freight_cost_model import estimate_corridor_cost

router = APIRouter()


@router.get("/")
async def list_corridors(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all corridors with latest performance metrics."""
    result = await db.execute(text("""
        SELECT
            c.corridor_id, c.name, c.description,
            c.origin_zones, c.dest_zones,
            c.origin_lat, c.origin_lon, c.dest_lat, c.dest_lon,
            cp.year, cp.total_tons, cp.total_value_usd,
            cp.total_ton_miles, cp.mode_breakdown,
            cp.estimated_cost, cp.cost_per_ton
        FROM corridors c
        LEFT JOIN corridor_performance cp ON c.corridor_id = cp.corridor_id
            AND cp.year = (SELECT MAX(year) FROM corridor_performance WHERE corridor_id = c.corridor_id)
        ORDER BY c.name
    """))
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/{corridor_id}/flows")
async def get_corridor_flows(
    corridor_id: UUID,
    year: int = Query(2022),
    commodity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get freight flow data for a specific corridor."""
    commodity_filter = "AND ff.sctg2 = :commodity" if commodity else ""
    result = await db.execute(text(f"""
        SELECT
            ff.sctg2, com.commodity_name,
            ff.mode_code, ff.mode_name,
            SUM(ff.tons_thousands) AS total_tons_k,
            SUM(ff.value_millions) AS total_value_m,
            SUM(ff.ton_miles_millions) AS total_tmiles_m
        FROM freight_flows ff
        JOIN corridors c ON ff.origin_zone_id = ANY(c.origin_zones)
                        AND ff.dest_zone_id = ANY(c.dest_zones)
        LEFT JOIN commodities com ON ff.sctg2 = com.sctg2
        WHERE c.corridor_id = :cid AND ff.year = :year
          {commodity_filter}
        GROUP BY ff.sctg2, com.commodity_name, ff.mode_code, ff.mode_name
        ORDER BY total_tons_k DESC NULLS LAST
    """), {"cid": corridor_id, "year": year, "commodity": commodity})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"corridor_id": str(corridor_id), "year": year}}


@router.get("/{corridor_id}/modes")
async def get_corridor_modes(
    corridor_id: UUID,
    year: int = Query(2022),
) -> dict[str, Any]:
    """Get mode breakdown for a specific corridor with cost estimates."""
    cost_data = await estimate_corridor_cost(str(corridor_id), year)
    return {"data": cost_data, "error": None, "meta": {}}


@router.get("/{corridor_id}/trends")
async def get_corridor_trends(
    corridor_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get year-over-year trends for a corridor."""
    result = await db.execute(text("""
        SELECT
            ff.year,
            ff.mode_code, ff.mode_name,
            SUM(ff.tons_thousands) AS total_tons_k,
            SUM(ff.value_millions) AS total_value_m,
            SUM(ff.ton_miles_millions) AS total_tmiles_m
        FROM freight_flows ff
        JOIN corridors c ON ff.origin_zone_id = ANY(c.origin_zones)
                        AND ff.dest_zone_id = ANY(c.dest_zones)
        WHERE c.corridor_id = :cid
        GROUP BY ff.year, ff.mode_code, ff.mode_name
        ORDER BY ff.year, ff.mode_code
    """), {"cid": corridor_id})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"corridor_id": str(corridor_id)}}
