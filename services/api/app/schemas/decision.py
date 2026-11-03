"""Decision schemas: create, update, output, version, and DNA models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OutcomeMetric(BaseModel):
    name: str
    unit: str = ""
    description: str = ""
    target: float | None = None


class DecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    objective: str = Field(default="", max_length=5000)
    time_horizon_days: int = Field(default=365, ge=1, le=100000)
    constraints: dict[str, Any] | None = None
    outcome_metrics: list[OutcomeMetric] | None = None


class DecisionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=10000)
    objective: str | None = Field(default=None, max_length=5000)
    time_horizon_days: int | None = Field(default=None, ge=1, le=100000)
    constraints: dict[str, Any] | None = None
    outcome_metrics: list[OutcomeMetric] | None = None
    status: str | None = Field(default=None, pattern="^(draft|active|archived)$")


class DecisionDNAUpdate(BaseModel):
    """Full Decision DNA model — variables, assumptions, formulas, dependencies."""
    decision_dna: dict[str, Any]
    change_summary: str = Field(default="", max_length=1000)


class DecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    owner_id: str
    title: str
    description: str
    objective: str
    time_horizon_days: int
    constraints: dict[str, Any] | None = None
    outcome_metrics: list[OutcomeMetric] | None = None
    status: str
    current_version_id: str | None = None
    created_at: datetime
    updated_at: datetime


class DecisionVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    decision_id: str
    version_number: int
    decision_dna: dict[str, Any]
    change_summary: str
    created_by: str | None = None
    created_at: datetime
