"""Simulation schemas — run creation, status, and result output."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SimulationCreate(BaseModel):
    """Request to create a simulation run."""
    decision_id: str
    scenario_id: str
    iterations: int = Field(default=10_000, ge=1, le=100_000)
    seed: int | None = None  # None = random seed
    threshold: float | None = None
    model_config_override: dict[str, Any] | None = None  # overrides applied to the model


class SimulationRunOut(BaseModel):
    """Status and metadata for a simulation run."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario_id: str
    decision_id: str
    workspace_id: str
    status: str
    iterations: int
    seed: int
    engine_version: str
    progress: int
    error_message: str | None = None
    requested_by: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class SimulationResultOut(BaseModel):
    """Full simulation results for a completed run."""
    run_id: str
    status: str
    objective: str
    iterations: int
    seed: int
    summary: dict[str, Any]
    distribution_buckets: dict[str, Any]
    sensitivity: dict[str, Any]
    elapsed_seconds: float | None = None
    config_snapshot: dict[str, Any] | None = None
    created_at: datetime | None = None


class SimulationRunListOut(BaseModel):
    """Paginated list of simulation runs."""
    items: list[SimulationRunOut]
    total: int
    page: int
    page_size: int
