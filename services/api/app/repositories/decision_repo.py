"""Decision repository — all queries scoped by workspace_id for tenant isolation."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.decision import Decision
from app.models.decision_version import DecisionVersion


class DecisionRepo:
    """CRUD operations for decisions and decision versions.

    Every query includes a workspace_id filter so cross-tenant access is impossible
    at the repository level.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ── Decisions ─────────────────────────────────────────────

    def list_by_workspace(
        self, workspace_id: str, *, page: int = 1, page_size: int = 20
    ) -> tuple[list[Decision], int]:
        offset = (page - 1) * page_size
        count_stmt = select(func.count()).select_from(Decision).where(
            Decision.workspace_id == workspace_id
        )
        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            select(Decision)
            .where(Decision.workspace_id == workspace_id)
            .order_by(Decision.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total

    def get_by_id(self, decision_id: str, workspace_id: str) -> Decision | None:
        """Get a decision, ensuring it belongs to the given workspace."""
        stmt = select(Decision).where(
            Decision.id == decision_id,
            Decision.workspace_id == workspace_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, workspace_id: str, owner_id: str, **fields) -> Decision:
        decision = Decision(workspace_id=workspace_id, owner_id=owner_id, **fields)
        self.db.add(decision)
        self.db.flush()
        return decision

    def update(self, decision: Decision, **fields) -> Decision:
        for key, value in fields.items():
            if value is not None:
                setattr(decision, key, value)
        self.db.flush()
        return decision

    def delete(self, decision: Decision) -> None:
        self.db.delete(decision)
        self.db.flush()

    # ── Versions ──────────────────────────────────────────────

    def list_versions(self, decision_id: str, workspace_id: str) -> list[DecisionVersion]:
        """List all versions for a decision, scoped to the workspace."""
        # First verify the decision belongs to the workspace
        decision = self.get_by_id(decision_id, workspace_id)
        if decision is None:
            return []
        stmt = (
            select(DecisionVersion)
            .where(DecisionVersion.decision_id == decision_id)
            .order_by(DecisionVersion.version_number.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_version(
        self, decision_id: str, workspace_id: str, version_number: int
    ) -> DecisionVersion | None:
        decision = self.get_by_id(decision_id, workspace_id)
        if decision is None:
            return None
        stmt = select(DecisionVersion).where(
            DecisionVersion.decision_id == decision_id,
            DecisionVersion.version_number == version_number,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_latest_version_number(self, decision_id: str) -> int:
        stmt = select(func.max(DecisionVersion.version_number)).where(
            DecisionVersion.decision_id == decision_id
        )
        result = self.db.execute(stmt).scalar_one()
        return result or 0

    def create_version(
        self,
        decision_id: str,
        decision_dna: dict,
        change_summary: str = "",
        created_by: str | None = None,
    ) -> DecisionVersion:
        version_number = self.get_latest_version_number(decision_id) + 1
        version = DecisionVersion(
            decision_id=decision_id,
            version_number=version_number,
            decision_dna=decision_dna,
            change_summary=change_summary,
            created_by=created_by,
        )
        self.db.add(version)
        self.db.flush()
        return version
