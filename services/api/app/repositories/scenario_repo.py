"""Scenario repository — all queries scoped by workspace_id for tenant isolation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scenario import Scenario


class ScenarioRepo:
    """CRUD operations for scenarios, all workspace-scoped."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_decision(self, decision_id: str, workspace_id: str) -> list[Scenario]:
        stmt = select(Scenario).where(
            Scenario.decision_id == decision_id,
            Scenario.workspace_id == workspace_id,
        ).order_by(Scenario.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, scenario_id: str, workspace_id: str) -> Scenario | None:
        stmt = select(Scenario).where(
            Scenario.id == scenario_id,
            Scenario.workspace_id == workspace_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        decision_id: str,
        workspace_id: str,
        name: str,
        description: str = "",
        assumption_overrides: dict | None = None,
    ) -> Scenario:
        scenario = Scenario(
            decision_id=decision_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
            assumption_overrides=assumption_overrides or {},
        )
        self.db.add(scenario)
        self.db.flush()
        return scenario

    def update(self, scenario: Scenario, **fields) -> Scenario:
        for key, value in fields.items():
            if value is not None:
                setattr(scenario, key, value)
        self.db.flush()
        return scenario

    def delete(self, scenario: Scenario) -> None:
        self.db.delete(scenario)
        self.db.flush()

    def duplicate(self, scenario: Scenario) -> Scenario:
        """Create a copy of a scenario with a '(copy)' suffix."""
        new = Scenario(
            decision_id=scenario.decision_id,
            workspace_id=scenario.workspace_id,
            name=f"{scenario.name} (copy)",
            description=scenario.description,
            assumption_overrides=scenario.assumption_overrides,
        )
        self.db.add(new)
        self.db.flush()
        return new
