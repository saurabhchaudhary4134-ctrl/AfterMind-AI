"""Simulation run and result repository — workspace-scoped for isolation."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.simulation_result import SimulationResult
from app.models.simulation_run import SimulationRun


class SimulationRepo:
    """CRUD operations for simulation runs and results."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Runs ──────────────────────────────────────────────────

    def get_by_id(self, run_id: str, workspace_id: str) -> SimulationRun | None:
        stmt = select(SimulationRun).where(
            SimulationRun.id == run_id,
            SimulationRun.workspace_id == workspace_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_decision(self, decision_id: str, workspace_id: str) -> list[SimulationRun]:
        stmt = select(SimulationRun).where(
            SimulationRun.decision_id == decision_id,
            SimulationRun.workspace_id == workspace_id,
        ).order_by(SimulationRun.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def list_by_scenario(self, scenario_id: str, workspace_id: str) -> list[SimulationRun]:
        stmt = select(SimulationRun).where(
            SimulationRun.scenario_id == scenario_id,
            SimulationRun.workspace_id == workspace_id,
        ).order_by(SimulationRun.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_latest_completed(self, scenario_id: str, workspace_id: str) -> SimulationRun | None:
        stmt = select(SimulationRun).where(
            SimulationRun.scenario_id == scenario_id,
            SimulationRun.workspace_id == workspace_id,
            SimulationRun.status == "completed",
        ).order_by(SimulationRun.created_at.desc()).limit(1)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, **fields) -> SimulationRun:
        run = SimulationRun(**fields)
        self.db.add(run)
        self.db.flush()
        return run

    def update_status(
        self,
        run: SimulationRun,
        status: str,
        progress: int | None = None,
        error_message: str | None = None,
    ) -> SimulationRun:
        run.status = status
        if progress is not None:
            run.progress = progress
        if error_message is not None:
            run.error_message = error_message
        if status == "running" and run.started_at is None:
            run.started_at = datetime.now(timezone.utc)
        if status in ("completed", "failed", "cancelled"):
            run.completed_at = datetime.now(timezone.utc)
        self.db.flush()
        return run

    # ── Results ───────────────────────────────────────────────

    def get_result(self, run_id: str, workspace_id: str) -> SimulationResult | None:
        run = self.get_by_id(run_id, workspace_id)
        if run is None or run.result is None:
            return None
        return run.result

    def create_result(self, run_id: str, summary: dict, distribution_buckets: dict,
                      sensitivity: dict) -> SimulationResult:
        result = SimulationResult(
            run_id=run_id,
            summary=summary,
            distribution_buckets=distribution_buckets,
            sensitivity=sensitivity,
        )
        self.db.add(result)
        self.db.flush()
        return result
