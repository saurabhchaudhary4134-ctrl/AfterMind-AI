"""Actual outcome repository — workspace-scoped for tenant isolation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.actual_outcome import ActualOutcome


class OutcomeRepo:
    """CRUD for actual outcome records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_decision(self, decision_id: str, workspace_id: str) -> list[ActualOutcome]:
        stmt = (
            select(ActualOutcome)
            .where(
                ActualOutcome.decision_id == decision_id,
                ActualOutcome.workspace_id == workspace_id,
            )
            .order_by(ActualOutcome.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        decision_id: str,
        workspace_id: str,
        metric_name: str,
        actual_value: float,
        recorded_by: str,
        notes: str = "",
    ) -> ActualOutcome:
        outcome = ActualOutcome(
            decision_id=decision_id,
            workspace_id=workspace_id,
            metric_name=metric_name,
            actual_value=actual_value,
            recorded_by=recorded_by,
            notes=notes,
        )
        self.db.add(outcome)
        self.db.flush()
        return outcome
