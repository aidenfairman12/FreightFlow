from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Prediction(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: UUID | None = None
    model_name: str
    model_version: str
    prediction_date: datetime | None = None
    target_period_start: datetime | None = None
    target_period_end: datetime | None = None
    target_variable: str
    predicted_value: float
    confidence_lower: float | None = None
    confidence_upper: float | None = None
    features_json: dict | None = None


class FeatureImportance(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    model_name: str
    model_version: str
    feature_name: str
    importance_score: float


class ModelInfo(BaseModel):
    """Metadata about a trained model."""
    model_config = ConfigDict(protected_namespaces=())
    model_name: str
    model_version: str
    target_variable: str
    feature_count: int
    training_samples: int
    r2_score: float | None = None
    mae: float | None = None
    trained_at: datetime | None = None
