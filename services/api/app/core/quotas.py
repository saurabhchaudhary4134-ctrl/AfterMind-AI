"""Quota enforcement — per-subscription-tier limits for simulations and LLM calls.

Quotas are enforced server-side. The frontend only shows UI; it never authorizes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.simulation_run import SimulationRun
from app.models.subscription import Subscription

# ── Tier definitions ──────────────────────────────────────────

@dataclass(frozen=True)
class TierQuota:
    simulations_per_month: int
    llm_calls_per_month: int
    max_iterations: int
    max_decisions: int


TIER_QUOTAS: dict[str, TierQuota] = {
    "free": TierQuota(
        simulations_per_month=100,
        llm_calls_per_month=10,
        max_iterations=10_000,
        max_decisions=3,
    ),
    "pro": TierQuota(
        simulations_per_month=1_000,
        llm_calls_per_month=100,
        max_iterations=50_000,
        max_decisions=50,
    ),
    "team": TierQuota(
        simulations_per_month=10_000,
        llm_calls_per_month=500,
        max_iterations=100_000,
        max_decisions=500,
    ),
    "business": TierQuota(
        simulations_per_month=100_000,
        llm_calls_per_month=5_000,
        max_iterations=100_000,
        max_decisions=10_000,
    ),
}

DEFAULT_QUOTA = TIER_QUOTAS["free"]


def _get_tier(db: Session, workspace_id: str) -> str:
    stmt = select(Subscription).where(Subscription.workspace_id == workspace_id)
    sub = db.execute(stmt).scalar_one_or_none()
    return sub.tier if sub else "free"


def get_quota(db: Session, workspace_id: str) -> TierQuota:
    tier = _get_tier(db, workspace_id)
    return TIER_QUOTAS.get(tier, DEFAULT_QUOTA)


def count_simulations_this_month(db: Session, workspace_id: str) -> int:
    """Count simulation runs created this calendar month."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    stmt = select(func.count()).select_from(SimulationRun).where(
        SimulationRun.workspace_id == workspace_id,
        SimulationRun.created_at >= month_start,
    )
    return db.execute(stmt).scalar_one() or 0


def check_simulation_quota(db: Session, workspace_id: str) -> tuple[bool, str]:
    """Return (allowed, reason). Returns False + message if over quota."""
    quota = get_quota(db, workspace_id)
    used = count_simulations_this_month(db, workspace_id)
    if used >= quota.simulations_per_month:
        return False, (
            f"Simulation quota exceeded. Your plan allows {quota.simulations_per_month} "
            f"simulations per month. Used: {used}. Upgrade your subscription to continue."
        )
    return True, ""


def get_usage_summary(db: Session, workspace_id: str) -> dict:
    """Return current usage and limits for a workspace."""
    tier = _get_tier(db, workspace_id)
    quota = TIER_QUOTAS.get(tier, DEFAULT_QUOTA)
    sims_used = count_simulations_this_month(db, workspace_id)
    return {
        "tier": tier,
        "simulations": {
            "used": sims_used,
            "limit": quota.simulations_per_month,
            "remaining": max(0, quota.simulations_per_month - sims_used),
        },
        "llm_calls": {
            "limit": quota.llm_calls_per_month,
            "note": "LLM call counting requires Redis (tracked separately in production)",
        },
        "max_iterations": quota.max_iterations,
        "max_decisions": quota.max_decisions,
    }
