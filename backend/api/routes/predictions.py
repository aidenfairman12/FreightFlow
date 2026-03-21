"""Phase 8: ML prediction endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from services.ml_pipeline import (
    run_ml_pipeline,
    detect_fuel_anomalies,
    score_route_profitability,
)

router = APIRouter()


@router.get("/feature-importance")
async def get_feature_importance(
    model_name: str = Query("cask_feature_importance"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return feature importance scores for a given model."""
    result = await db.execute(text("""
        SELECT feature_name, importance_score
        FROM ml_feature_importance
        WHERE model_name = :name
        ORDER BY importance_score DESC
    """), {"name": model_name})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"model": model_name, "count": len(rows)}}


@router.get("/forecasts")
async def get_forecasts(
    target: str = Query("total_cask"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Return latest predictions for a target variable."""
    result = await db.execute(text("""
        SELECT
            model_name, model_version, target_variable,
            predicted_value, confidence_lower, confidence_upper,
            target_period_start, target_period_end, prediction_date
        FROM ml_predictions
        WHERE target_variable = :target
        ORDER BY target_period_start DESC
        LIMIT :limit
    """), {"target": target, "limit": limit})
    rows = [dict(r) for r in result.mappings()]
    return {"data": rows, "error": None, "meta": {"target": target, "count": len(rows)}}


@router.get("/anomalies")
async def get_fuel_anomalies(
    hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    """Return flights with anomalous fuel burn in the last N hours."""
    anomalies = await detect_fuel_anomalies(hours)
    return {"data": anomalies, "error": None, "meta": {"hours": hours, "count": len(anomalies)}}


@router.get("/route-profitability")
async def get_route_profitability() -> dict[str, Any]:
    """Return route profitability scores."""
    routes = await score_route_profitability()
    if not routes:
        return {"data": [], "error": None, "meta": {"count": 0}}
    return {"data": routes, "error": None, "meta": {"count": len(routes)}}


@router.get("/models")
async def list_models(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """List all trained models with their latest metadata."""
    result = await db.execute(text("""
        SELECT
            model_name,
            model_version,
            COUNT(*) AS feature_count,
            MAX(created_at) AS last_trained
        FROM ml_feature_importance
        GROUP BY model_name, model_version
        ORDER BY MAX(created_at) DESC
    """))
    models = [dict(r) for r in result.mappings()]

    # Add prediction models
    pred_result = await db.execute(text("""
        SELECT
            model_name,
            model_version,
            target_variable,
            COUNT(*) AS prediction_count,
            MAX(prediction_date) AS last_predicted
        FROM ml_predictions
        GROUP BY model_name, model_version, target_variable
        ORDER BY MAX(prediction_date) DESC
    """))
    for row in pred_result.mappings():
        models.append(dict(row))

    return {"data": models, "error": None, "meta": {"count": len(models)}}


@router.post("/train")
async def trigger_ml_training() -> dict[str, Any]:
    """Manually trigger ML pipeline training."""
    results = await run_ml_pipeline()
    return {"data": results, "error": None, "meta": {"triggered": True}}
