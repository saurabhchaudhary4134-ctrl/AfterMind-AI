"""Workspace repository — all queries scoped by workspace_id for isolation."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember


class WorkspaceRepo:
    """CRUD operations for workspaces and membership."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, workspace_id: str) -> Workspace | None:
        return self.db.get(Workspace, workspace_id)

    def get_by_slug(self, slug: str) -> Workspace | None:
        stmt = select(Workspace).where(Workspace.slug == slug)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_user(self, user_id: str) -> list[Workspace]:
        """List all workspaces where the user is a member."""
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def create(self, name: str, slug: str, owner_id: str) -> Workspace:
        ws = Workspace(name=name, slug=slug, owner_id=owner_id)
        self.db.add(ws)
        self.db.flush()
        return ws

    # ── Membership ────────────────────────────────────────────

    def get_membership(self, workspace_id: str, user_id: str) -> WorkspaceMember | None:
        stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def add_member(self, workspace_id: str, user_id: str, role: str = "member") -> WorkspaceMember:
        member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
        self.db.add(member)
        self.db.flush()
        return member

    def update_member_role(self, member: WorkspaceMember, role: str) -> WorkspaceMember:
        member.role = role
        self.db.flush()
        return member

    def remove_member(self, member: WorkspaceMember) -> None:
        self.db.delete(member)
        self.db.flush()

    def list_members(self, workspace_id: str) -> list[WorkspaceMember]:
        stmt = select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        return list(self.db.execute(stmt).scalars().all())
