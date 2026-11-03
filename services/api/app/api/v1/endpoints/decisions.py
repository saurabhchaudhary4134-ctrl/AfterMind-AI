"""Decision endpoints: CRUD, version history, and DNA updates."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.decision_repo import DecisionRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.decision import (
    DecisionCreate,
    DecisionDNAUpdate,
    DecisionOut,
    DecisionUpdate,
    DecisionVersionOut,
)

router = APIRouter(tags=["decisions"])


def _require_membership(workspace_id: str, user: User, db: Session) -> str:
    """Verify membership and return the workspace_id. Raises 403 if not a member."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    return workspace_id


@router.get("/decisions", response_model=dict)
async def list_decisions(
    workspace_id: str = Query(..., description="Filter decisions by workspace"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List decisions in a workspace (paginated)."""
    _require_membership(workspace_id, user, db)
    items, total = DecisionRepo(db).list_by_workspace(workspace_id, page=page, page_size=page_size)
    return {
        "items": [DecisionOut.model_validate(d).model_dump(mode="json") for d in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("/decisions", response_model=DecisionOut, status_code=status.HTTP_201_CREATED)
async def create_decision(
    payload: DecisionCreate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new decision in the given workspace."""
    _require_membership(workspace_id, user, db)
    decision = DecisionRepo(db).create(
        workspace_id=workspace_id,
        owner_id=user.id,
        title=payload.title,
        description=payload.description,
        objective=payload.objective,
        time_horizon_days=payload.time_horizon_days,
        constraints=payload.constraints,
        outcome_metrics=[m.model_dump() for m in payload.outcome_metrics] if payload.outcome_metrics else None,
    )
    db.commit()
    return DecisionOut.model_validate(decision)


@router.get("/decisions/{decision_id}", response_model=DecisionOut)
async def get_decision(
    decision_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single decision. workspace_id must match for isolation."""
    _require_membership(workspace_id, user, db)
    decision = DecisionRepo(db).get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return DecisionOut.model_validate(decision)


@router.put("/decisions/{decision_id}", response_model=DecisionOut)
async def update_decision(
    decision_id: str,
    payload: DecisionUpdate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update decision metadata. Does NOT create a new version (that's DNA-only)."""
    _require_membership(workspace_id, user, db)
    repo = DecisionRepo(db)
    decision = repo.get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    fields = payload.model_dump(exclude_unset=True)
    # Convert outcome_metrics list to plain dicts for JSON storage
    if "outcome_metrics" in fields and fields["outcome_metrics"] is not None:
        fields["outcome_metrics"] = [m.model_dump() for m in payload.outcome_metrics]
    repo.update(decision, **fields)
    db.commit()
    return DecisionOut.model_validate(decision)


@router.delete("/decisions/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decision(
    decision_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a decision and all its versions, scenarios, and simulations."""
    _require_membership(workspace_id, user, db)
    repo = DecisionRepo(db)
    decision = repo.get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    repo.delete(decision)
    db.commit()


# ── Version history ──────────────────────────────────────────

@router.get("/decisions/{decision_id}/versions", response_model=list[DecisionVersionOut])
async def list_versions(
    decision_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all versions (version history) for a decision."""
    _require_membership(workspace_id, user, db)
    versions = DecisionRepo(db).list_versions(decision_id, workspace_id)
    return [DecisionVersionOut.model_validate(v) for v in versions]


@router.get("/decisions/{decision_id}/versions/{version_number}", response_model=DecisionVersionOut)
async def get_version(
    decision_id: str,
    version_number: int,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a specific version of a decision's DNA."""
    _require_membership(workspace_id, user, db)
    version = DecisionRepo(db).get_version(decision_id, workspace_id, version_number)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return DecisionVersionOut.model_validate(version)


@router.put("/decisions/{decision_id}/dna", response_model=DecisionVersionOut)
async def update_dna(
    decision_id: str,
    payload: DecisionDNAUpdate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the Decision DNA. Creates a new immutable version."""
    _require_membership(workspace_id, user, db)
    repo = DecisionRepo(db)
    decision = repo.get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")

    version = repo.create_version(
        decision_id=decision_id,
        decision_dna=payload.decision_dna,
        change_summary=payload.change_summary,
        created_by=user.id,
    )
    decision.current_version_id = version.id
    decision.status = "active"
    repo.update(decision)
    db.commit()
    return DecisionVersionOut.model_validate(version)
