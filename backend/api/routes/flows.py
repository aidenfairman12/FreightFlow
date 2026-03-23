"""Freight flow query endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db

router = APIRouter()


@router.get("/")
async def query_flows(
    year: int = Query(2022),
    commodity: str | None = Query(None),
    mode: int | None = Query(None),
    origin: int | None = Query(None),
    dest: int | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Query freight flows with optional filters."""
    conditions = ["ff.year = :year"]
    params: dict = {"year": year, "limit": limit}

    if commodity:
        conditions.append("ff.sctg2 = :commodity")
        params["commodity"] = commodity
    if mode:
        conditions.append("ff.mode_code = :mode")
        params["mode"] = mode
    if origin:
        conditions.append("ff.origin_zone_id = :origin")
        params["origin"] = origin
    if dest:
        conditions.append("ff.dest_zone_id = :dest")
        params["dest"] = dest

    where = " AND ".join(conditions)
    result = await db.execute(text(f"""
        SELECT
            ff.origin_zone_id, oz.zone_name AS origin_name,
            ff.dest_zone_id, dz.zone_name AS dest_name,
            ff.sctg2, com.commodity_name,
            ff.mode_code, ff.mode_name,
            ff.year,
            ff.tons_thousands, ff.value_millions, ff.ton_miles_millions
        FROM freight_flows ff
        LEFT JOIN faf_zones oz ON ff.origin_zone_id = oz.zone_id
        LEFT JOIN faf_zones dz ON ff.dest_zone_id = dz.zone_id
        LEFT JOIN commodities com ON ff.sctg2 = com.sctg2
        WHERE {where}
        ORDER BY ff.tons_thousands DESC NULLS LAST
        LIMIT :limit
    """), params)
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/top-corridors")
async def get_top_corridors(
    year: int = Query(2022),
    commodity: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Top origin-destination pairs by freight volume."""
    commodity_filter = "AND ff.sctg2 = :commodity" if commodity else ""
    result = await db.execute(text(f"""
        SELECT
            ff.origin_zone_id, oz.zone_name AS origin_name,
            ff.dest_zone_id, dz.zone_name AS dest_name,
            SUM(ff.tons_thousands) AS total_tons_k,
            SUM(ff.value_millions) AS total_value_m,
            SUM(ff.ton_miles_millions) AS total_tmiles_m
        FROM freight_flows ff
        LEFT JOIN faf_zones oz ON ff.origin_zone_id = oz.zone_id
        LEFT JOIN faf_zones dz ON ff.dest_zone_id = dz.zone_id
        WHERE ff.year = :year
          {commodity_filter}
        GROUP BY ff.origin_zone_id, oz.zone_name, ff.dest_zone_id, dz.zone_name
        ORDER BY total_tons_k DESC NULLS LAST
        LIMIT :limit
    """), {"year": year, "commodity": commodity, "limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows), "year": year}}


@router.get("/mode-trends")
async def get_mode_trends(
    commodity: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Mode share trends across all years."""
    commodity_filter = "AND ff.sctg2 = :commodity" if commodity else ""
    result = await db.execute(text(f"""
        SELECT
            ff.year,
            ff.mode_code, ff.mode_name,
            SUM(ff.tons_thousands) AS total_tons_k,
            SUM(ff.value_millions) AS total_value_m,
            SUM(ff.ton_miles_millions) AS total_tmiles_m
        FROM freight_flows ff
        WHERE 1=1
          {commodity_filter}
        GROUP BY ff.year, ff.mode_code, ff.mode_name
        ORDER BY ff.year, ff.mode_code
    """), {"commodity": commodity})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/zones")
async def list_zones(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all FAF zones with coordinates."""
    result = await db.execute(text("""
        SELECT zone_id, zone_name, state_name, latitude, longitude, zone_type
        FROM faf_zones
        ORDER BY zone_id
    """))
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}
