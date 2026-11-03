"""Actual outcome and forecast evaluation schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OutcomeCreate(BaseModel):
    metric_name: str = Field(min_length=1, max_length=255)
    actual_value: float
    notes: str = Field(default="", max_length=2000)


class OutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    decision_id: str
    workspace_id: str
    metric_name: str
    actual_value: float
    notes: str
    recorded_by: str | None
    created_at: datetime


class ForecastEvaluation(BaseModel):
    """Forecast error metrics computed from actual outcomes vs simulation predictions.

    Clearly distinguishes facts (actual outcomes), model estimates (simulated values),
    and displays sample sizes and limitations.
    """
    decision_id: str
    n_outcomes: int
    metrics: list[MetricEval]
    limitation_note: str


class MetricEval(BaseModel):
    metric_name: str
    actual_value: float
    simulated_p50: float | None = None
    simulated_mean: float | None = None
    absolute_error: float | None = None
    pct_error: float | None = None
    note: str = ""
