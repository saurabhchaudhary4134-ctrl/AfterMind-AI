"""Scenario endpoints: CRUD, duplicate, and side-by-side comparison."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.decision_repo import DecisionRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.simulation_repo import SimulationRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.scenario import ScenarioCreate, ScenarioOut, ScenarioUpdate

router = APIRouter(tags=["scenarios"])


def _verify_access(workspace_id: str, decision_id: str, user: User, db: Session):
    """Verify workspace membership and that the decision belongs to the workspace."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    decision = DecisionRepo(db).get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return decision


@router.get("/scenarios", response_model=list[ScenarioOut])
async def list_scenarios(
    decision_id: str = Query(...),
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all scenarios for a decision."""
    _verify_access(workspace_id, decision_id, user, db)
    return ScenarioRepo(db).list_by_decision(decision_id, workspace_id)


@router.post("/scenarios", response_model=ScenarioOut, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    payload: ScenarioCreate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new scenario for a decision."""
    _verify_access(workspace_id, payload.decision_id, user, db)
    scenario = ScenarioRepo(db).create(
        decision_id=payload.decision_id,
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        assumption_overrides=payload.assumption_overrides,
    )
    db.commit()
    return ScenarioOut.model_validate(scenario)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioOut)
async def get_scenario(
    scenario_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single scenario."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    scenario = ScenarioRepo(db).get_by_id(scenario_id, workspace_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    return ScenarioOut.model_validate(scenario)


@router.put("/scenarios/{scenario_id}", response_model=ScenarioOut)
async def update_scenario(
    scenario_id: str,
    payload: ScenarioUpdate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a scenario's name, description, or overrides."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    repo = ScenarioRepo(db)
    scenario = repo.get_by_id(scenario_id, workspace_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    fields = payload.model_dump(exclude_unset=True)
    repo.update(scenario, **fields)
    db.commit()
    return ScenarioOut.model_validate(scenario)


@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a scenario."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    repo = ScenarioRepo(db)
    scenario = repo.get_by_id(scenario_id, workspace_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    repo.delete(scenario)
    db.commit()


@router.post("/scenarios/{scenario_id}/duplicate", response_model=ScenarioOut,
             status_code=status.HTTP_201_CREATED)
async def duplicate_scenario(
    scenario_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Duplicate a scenario with its assumption overrides."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    repo = ScenarioRepo(db)
    scenario = repo.get_by_id(scenario_id, workspace_id)
    if scenario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scenario not found")
    new_scenario = repo.duplicate(scenario)
    db.commit()
    return ScenarioOut.model_validate(new_scenario)


@router.get("/scenarios/compare", tags=["scenarios"])
async def compare_scenarios(
    decision_id: str = Query(...),
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare scenarios side-by-side using their latest completed simulation results."""
    _verify_access(workspace_id, decision_id, user, db)
    scenarios = ScenarioRepo(db).list_by_decision(decision_id, workspace_id)
    sim_repo = SimulationRepo(db)

    comparison = []
    for sc in scenarios:
        latest_run = sim_repo.get_latest_completed(sc.id, workspace_id)
        entry = {
            "scenario_id": sc.id,
            "scenario_name": sc.name,
            "has_results": latest_run is not None,
            "run_id": latest_run.id if latest_run else None,
            "summary": None,
        }
        if latest_run and latest_run.result:
            entry["summary"] = latest_run.result.summary
        comparison.append(entry)

    return {"scenarios": comparison}
