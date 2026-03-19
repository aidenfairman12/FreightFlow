from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db

router = APIRouter()


@router.get("/fuel")
async def get_fuel_analytics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Top-20 fuel consumers in the last hour."""
    result = await db.execute(text("""
        SELECT
            icao24,
            callsign,
            AVG(fuel_flow_kg_s) AS avg_fuel_kg_s,
            AVG(co2_kg_s)       AS avg_co2_kg_s,
            COUNT(*)            AS samples
        FROM state_vectors
        WHERE time > NOW() - INTERVAL '1 hour'
          AND on_ground = false
          AND fuel_flow_kg_s IS NOT NULL
        GROUP BY icao24, callsign
        ORDER BY avg_fuel_kg_s DESC
        LIMIT 20
    """))
    return {"data": list(result.mappings()), "error": None, "meta": {}}


@router.get("/network")
async def get_network_analytics() -> dict[str, Any]:
    """Route frequency and hub connectivity metrics via NetworkX."""
    # TODO Phase 3: build graph from route_analytics table
    return {"data": [], "error": None, "meta": {}}


@router.get("/emissions")
async def get_emissions(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Fleet-wide CO2 and fuel burn aggregates for the last 10 minutes."""
    result = await db.execute(text("""
        SELECT
            COUNT(DISTINCT icao24)           AS aircraft_count,
            COALESCE(SUM(co2_kg_s), 0)       AS total_co2_kg_s,
            COALESCE(SUM(fuel_flow_kg_s), 0) AS total_fuel_kg_s
        FROM state_vectors
        WHERE time > NOW() - INTERVAL '10 minutes'
          AND on_ground = false
          AND co2_kg_s IS NOT NULL
    """))
    row = result.mappings().one()
    return {"data": dict(row), "error": None, "meta": {}}
