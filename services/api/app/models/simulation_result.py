"""Simulation result ORM model — immutable computed results, one per run."""

from __future__ import annotations

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKey


class SimulationResult(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "simulation_results"

    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    distribution_buckets: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    sensitivity: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    raw_percentiles_cache: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped["SimulationRun"] = relationship("SimulationRun", back_populates="result")
