"""Decision ORM model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class Decision(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "decisions"

    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    time_horizon_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    constraints: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    outcome_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # Plain pointer to the latest version — no FK to avoid circular dependency
    # with decision_versions.decision_id. Relationship is enforced at app level.
    current_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
