from typing import Any

from fastapi import APIRouter, Query

from services.schedule_imputation import (
    get_schedule_summary,
    get_imputed_flights,
    run_imputation_cycle,
)

router = APIRouter()


@router.get("/patterns")
async def get_schedule_patterns() -> dict[str, Any]:
    """Return learned weekly flight schedule patterns."""
    patterns = await get_schedule_summary()
    return {
        "data": patterns,
        "error": None,
        "meta": {"count": len(patterns)},
    }


@router.get("/imputed")
async def get_imputed(
    status: str | None = Query(None, regex="^(expected|confirmed|missed)$"),
    limit: int = Query(100, ge=1, le=1000),
) -> dict[str, Any]:
    """Return imputed flights, optionally filtered by status."""
    flights = await get_imputed_flights(status=status, limit=limit)
    return {
        "data": flights,
        "error": None,
        "meta": {"count": len(flights), "filter": status},
    }


@router.post("/run")
async def trigger_imputation_cycle() -> dict[str, Any]:
    """Manually trigger a full imputation cycle (learn + impute + reconcile)."""
    result = await run_imputation_cycle()
    return {"data": result, "error": None, "meta": None}
