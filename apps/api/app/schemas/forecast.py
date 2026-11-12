from datetime import datetime
from typing import Literal

from pydantic import BaseModel, field_validator

from app.analytics.engine import utc
from app.schemas.api import ORMModel


class ForecastOut(ORMModel):
    id: int
    repository_id: int
    full_name: str = ""
    language: str | None = None
    model_version: str
    issued_at: datetime
    as_of: datetime
    target_at: datetime
    stars_at_origin: int
    projected_growth: float
    baseline_growth: float
    breakout_threshold: int
    breakout_ratio: float
    predicted_breakout: bool
    features: dict[str, float]
    explanation: list[str]
    stale: bool = False
    demo: bool
    evaluation_status: Literal["pending", "evaluated", "unavailable"]
    realized_growth: float | None
    actual_breakout: bool | None
    outcome_at: datetime | None

    @field_validator("issued_at", "as_of", "target_at", "outcome_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None) -> datetime | None:
        return utc(value) if value is not None else None


class ForecastPage(BaseModel):
    items: list[ForecastOut]
    total: int
    page: int
    page_size: int
    demo: bool
    model_version: str


class ForecastStatus(BaseModel):
    status: Literal["ready", "insufficient_history", "stale", "inactive"]
    reason: str | None = None
    forecast: ForecastOut | None = None
    demo: bool


class ValidationOut(BaseModel):
    model_version: str
    demo: bool
    evaluated: int
    pending: int
    unavailable: int
    predicted_breakouts: int
    actual_breakouts: int
    precision: float | None
    recall: float | None
    mean_absolute_error: float | None
    baseline_mean_absolute_error: float | None
