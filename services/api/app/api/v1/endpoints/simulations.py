"""Simulation endpoints: create run, status, results, cancel, list."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.simulation_repo import SimulationRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.simulation import SimulationCreate, SimulationResultOut, SimulationRunOut
from app.services.simulation_service import SimulationError, SimulationService

router = APIRouter(tags=["simulations"])


@router.post("/simulations", response_model=SimulationRunOut,
             status_code=status.HTTP_202_ACCEPTED)
async def create_simulation(
    payload: SimulationCreate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a simulation run. Returns 202 Accepted with the run record."""
    service = SimulationService(db)
    try:
        # Enforce quota before creating the run
        from app.core.quotas import check_simulation_quota
        allowed, reason = check_simulation_quota(db, workspace_id)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=reason)

        run_id = service.create_run(
            workspace_id=workspace_id,
            decision_id=payload.decision_id,
            scenario_id=payload.scenario_id,
            user_id=user.id,
            iterations=payload.iterations,
            seed=payload.seed,
            threshold=payload.threshold,
            model_config_override=payload.model_config_override,
        )
    except SimulationError as exc:
        status_code = _error_status(str(exc))
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    return SimulationRunOut.model_validate(run)


@router.get("/simulations/{run_id}", response_model=SimulationRunOut)
async def get_simulation(
    run_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the status of a simulation run."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    return SimulationRunOut.model_validate(run)


@router.get("/simulations/{run_id}/results", response_model=SimulationResultOut)
async def get_simulation_results(
    run_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get simulation results. Only available for completed runs."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    if run.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Simulation is {run.status}, not completed",
        )
    result = run.result
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Results not found")

    return SimulationResultOut(
        run_id=run_id,
        status=run.status,
        objective=run.config_snapshot.get("objective", ""),
        iterations=run.iterations,
        seed=run.seed,
        summary=result.summary,
        distribution_buckets=result.distribution_buckets,
        sensitivity=result.sensitivity,
        elapsed_seconds=None,
        config_snapshot=run.config_snapshot,
        created_at=result.created_at,
    )


@router.post("/simulations/{run_id}/cancel", response_model=SimulationRunOut)
async def cancel_simulation(
    run_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel a queued or running simulation."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    service = SimulationService(db)
    cancelled = service.cancel_run(run_id, workspace_id)
    if not cancelled:
        run = SimulationRepo(db).get_by_id(run_id, workspace_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel a {run.status} simulation",
        )
    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    return SimulationRunOut.model_validate(run)


@router.get("/simulations", response_model=dict)
async def list_simulations(
    decision_id: str = Query(...),
    workspace_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List simulation runs for a decision (paginated)."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    runs = SimulationRepo(db).list_by_decision(decision_id, workspace_id)
    total = len(runs)
    offset = (page - 1) * page_size
    page_items = runs[offset:offset + page_size]
    return {
        "items": [SimulationRunOut.model_validate(r).model_dump(mode="json") for r in page_items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _error_status(message: str) -> int:
    """Map error messages to HTTP status codes."""
    if "not a member" in message.lower():
        return 403
    if "not found" in message.lower():
        return 404
    if "no dna" in message.lower():
        return 409
    if "iterations" in message.lower():
        return 422
    return 400
