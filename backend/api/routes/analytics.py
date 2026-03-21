from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.route_performance import (
    compute_route_performance,
    get_route_performance_summary,
    get_flight_deviations,
)

router = APIRouter()


@router.get("/fuel")
async def get_fuel_analytics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Top-20 SWISS fuel consumers in the last hour."""
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
          AND callsign LIKE 'SWR%'
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


@router.get("/route-performance")
async def get_route_perf(
    category: str | None = Query(None, pattern="^(overperforming|average|underperforming)$"),
    sort_by: str = Query("performance_score"),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    """Route performance: baselines vs recent actuals with deviation scores."""
    routes = await get_route_performance_summary(
        category=category, sort_by=sort_by, limit=limit,
    )
    return {
        "data": routes,
        "error": None,
        "meta": {"count": len(routes), "filter": category, "sort": sort_by},
    }


@router.get("/flight-deviations")
async def get_flight_devs(
    origin: str | None = Query(None),
    destination: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    """Individual flight deviations from route baselines."""
    flights = await get_flight_deviations(
        origin=origin, destination=destination, limit=limit,
    )
    return {
        "data": flights,
        "error": None,
        "meta": {"count": len(flights), "origin": origin, "destination": destination},
    }


@router.post("/route-performance/compute")
async def trigger_route_performance() -> dict[str, Any]:
    """Manually trigger route performance computation."""
    count = await compute_route_performance()
    return {
        "data": {"routes_scored": count},
        "error": None,
        "meta": {"triggered": True},
    }


@router.get("/emissions")
async def get_emissions(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """SWISS fleet CO2 and fuel burn aggregates for the last 10 minutes."""
    result = await db.execute(text("""
        SELECT
            COUNT(DISTINCT icao24)           AS aircraft_count,
            COALESCE(SUM(co2_kg_s), 0)       AS total_co2_kg_s,
            COALESCE(SUM(fuel_flow_kg_s), 0) AS total_fuel_kg_s
        FROM state_vectors
        WHERE time > NOW() - INTERVAL '10 minutes'
          AND on_ground = false
          AND co2_kg_s IS NOT NULL
          AND callsign LIKE 'SWR%'
    """))
    row = result.mappings().one()
    return {"data": dict(row), "error": None, "meta": {}}
