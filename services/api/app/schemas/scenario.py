"""Scenario schemas — named alternatives with assumption overrides."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ScenarioCreate(BaseModel):
    decision_id: str
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=5000)
    assumption_overrides: dict[str, Any] = Field(default_factory=dict)


class ScenarioUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    assumption_overrides: dict[str, Any] | None = None


class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    decision_id: str
    workspace_id: str
    name: str
    description: str
    assumption_overrides: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScenarioComparison(BaseModel):
    """Side-by-side comparison of scenario summary statistics."""
    scenarios: list[dict[str, Any]]
