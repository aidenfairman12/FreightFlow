"""Phase 5: Operational KPI endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.kpi_aggregator import compute_kpis

router = APIRouter()


@router.get("/current")
async def get_current_kpis(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Return the most recent operational KPIs for SWISS."""
    result = await db.execute(text("""
        SELECT * FROM operational_kpis
        WHERE airline_code = 'SWR'
        ORDER BY period_start DESC
        LIMIT 1
    """))
    row = result.mappings().first()
    if not row:
        return {"data": None, "error": "No KPI data available yet", "meta": {}}
    return {"data": dict(row), "error": None, "meta": {}}


@router.get("/history")
async def get_kpi_history(
    period_type: str = Query("weekly", pattern="^(weekly|monthly)$"),
    limit: int = Query(52, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return historical KPIs for trend analysis."""
    result = await db.execute(text("""
        SELECT * FROM operational_kpis
        WHERE airline_code = 'SWR' AND period_type = :ptype
        ORDER BY period_start DESC
        LIMIT :limit
    """), {"ptype": period_type, "limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.get("/fleet")
async def get_fleet_utilization(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Real-time fleet utilization for SWISS aircraft."""
    result = await db.execute(text("""
        WITH with_deltas AS (
            SELECT
                icao24, callsign, on_ground, fuel_flow_kg_s, time,
                LEAST(
                    COALESCE(
                        EXTRACT(EPOCH FROM
                            time - LAG(time) OVER (PARTITION BY icao24 ORDER BY time)
                        ),
                        10
                    ),
                    60
                ) AS dt_seconds
            FROM state_vectors
            WHERE time > NOW() - :hours * INTERVAL '1 hour'
              AND callsign LIKE 'SWR%'
        )
        SELECT
            icao24,
            MAX(callsign) AS callsign,
            COALESCE(SUM(dt_seconds) FILTER (WHERE on_ground = false), 0) / 3600.0 AS block_hours,
            COUNT(*) AS observations,
            MIN(time) AS first_seen,
            MAX(time) AS last_seen,
            AVG(fuel_flow_kg_s) FILTER (WHERE fuel_flow_kg_s IS NOT NULL) AS avg_fuel
        FROM with_deltas
        GROUP BY icao24
        ORDER BY block_hours DESC
    """), {"hours": hours})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows), "hours": hours}}


@router.get("/routes")
async def get_route_frequency(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """SWISS route frequency from route_analytics."""
    result = await db.execute(text("""
        SELECT
            origin_icao,
            destination_icao,
            flight_count,
            avg_fuel_kg,
            avg_duration_min,
            last_updated
        FROM route_analytics
        ORDER BY flight_count DESC
        LIMIT 50
    """))
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"count": len(rows)}}


@router.post("/compute")
async def trigger_kpi_computation(
    period_type: str = Query("weekly"),
) -> dict[str, Any]:
    """Manually trigger KPI computation for the current period."""
    now = datetime.utcnow()
    if period_type == "weekly":
        start = now - timedelta(days=now.weekday(), hours=now.hour,
                                minutes=now.minute, seconds=now.second)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    result = await compute_kpis(start, now, period_type)
    if result:
        return {"data": result, "error": None, "meta": {"triggered": True}}
    return {"data": None, "error": "Insufficient data for KPI computation", "meta": {}}
