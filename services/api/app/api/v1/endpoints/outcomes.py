"""Actual outcome endpoints and forecast evaluation."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.decision_repo import DecisionRepo
from app.repositories.outcome_repo import OutcomeRepo
from app.repositories.simulation_repo import SimulationRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.schemas.outcome import ForecastEvaluation, MetricEval, OutcomeCreate, OutcomeOut

router = APIRouter(tags=["outcomes"])


def _require(workspace_id: str, decision_id: str, user: User, db: Session):
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a workspace member")
    decision = DecisionRepo(db).get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Decision not found")
    return decision


@router.post(
    "/decisions/{decision_id}/outcomes",
    response_model=OutcomeOut,
    status_code=status.HTTP_201_CREATED,
)
async def record_outcome(
    decision_id: str,
    payload: OutcomeCreate,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record an actual outcome for a decision metric."""
    _require(workspace_id, decision_id, user, db)
    outcome = OutcomeRepo(db).create(
        decision_id=decision_id,
        workspace_id=workspace_id,
        metric_name=payload.metric_name,
        actual_value=payload.actual_value,
        recorded_by=user.id,
        notes=payload.notes,
    )
    db.commit()
    return OutcomeOut.model_validate(outcome)


@router.get("/decisions/{decision_id}/outcomes", response_model=list[OutcomeOut])
async def list_outcomes(
    decision_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all recorded actual outcomes for a decision."""
    _require(workspace_id, decision_id, user, db)
    outcomes = OutcomeRepo(db).list_by_decision(decision_id, workspace_id)
    return [OutcomeOut.model_validate(o) for o in outcomes]


@router.get("/decisions/{decision_id}/forecast-eval", response_model=ForecastEvaluation)
async def forecast_evaluation(
    decision_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compute forecast error metrics comparing actuals to simulation predictions.

    Clearly states sample sizes and limitations. Never claims statistical significance
    without adequate data.
    """
    _require(workspace_id, decision_id, user, db)
    outcomes = OutcomeRepo(db).list_by_decision(decision_id, workspace_id)

    if not outcomes:
        return ForecastEvaluation(
            decision_id=decision_id,
            n_outcomes=0,
            metrics=[],
            limitation_note=(
                "No actual outcomes recorded yet. Record outcomes after the decision period "
                "to evaluate forecast accuracy."
            ),
        )

    # Get the most recent completed simulation run for this decision
    sim_repo = SimulationRepo(db)
    all_runs = sim_repo.list_by_decision(decision_id, workspace_id)
    completed = [r for r in all_runs if r.status == "completed" and r.result is not None]
    latest_result = completed[0].result if completed else None

    metric_evals: list[MetricEval] = []
    for outcome in outcomes:
        simulated_p50: float | None = None
        simulated_mean: float | None = None
        abs_error: float | None = None
        pct_error: float | None = None
        note = ""

        if latest_result and outcome.metric_name == _get_objective(completed[0].config_snapshot):
            simulated_p50 = latest_result.summary.get("p50")
            simulated_mean = latest_result.summary.get("mean")
            if simulated_p50 is not None:
                abs_error = abs(outcome.actual_value - simulated_p50)
                if simulated_p50 != 0:
                    pct_error = abs(outcome.actual_value - simulated_p50) / abs(simulated_p50)
            note = "Compared to most recent completed simulation (P50 and mean)."
        else:
            note = "No matching simulation result found for this metric."

        metric_evals.append(MetricEval(
            metric_name=outcome.metric_name,
            actual_value=outcome.actual_value,
            simulated_p50=simulated_p50,
            simulated_mean=simulated_mean,
            absolute_error=abs_error,
            pct_error=pct_error,
            note=note,
        ))

    n = len(outcomes)
    limitation = (
        f"Based on {n} recorded outcome(s). "
        + ("Statistical calibration requires more data." if n < 10 else "")
    )

    return ForecastEvaluation(
        decision_id=decision_id,
        n_outcomes=n,
        metrics=metric_evals,
        limitation_note=limitation,
    )


def _get_objective(config_snapshot: dict) -> str:
    return config_snapshot.get("objective", "")


# ── Reports ───────────────────────────────────────────────────

@router.get("/reports/{run_id}")
async def get_report(
    run_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a full report for a completed simulation run."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a workspace member")

    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    if run.status != "completed" or run.result is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Simulation not completed")

    result = run.result
    return {
        "run_id": run_id,
        "status": run.status,
        "engine_version": run.engine_version,
        "seed": run.seed,
        "iterations": run.iterations,
        "objective": run.config_snapshot.get("objective", ""),
        "summary": result.summary,
        "distribution_buckets": result.distribution_buckets,
        "sensitivity": result.sensitivity,
        "config_snapshot": run.config_snapshot,
        "created_at": result.created_at.isoformat() if result.created_at else None,
    }


@router.get("/reports/{run_id}/export")
async def export_report(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Export a simulation report as JSON or CSV."""
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a workspace member")

    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    if run.status != "completed" or run.result is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Simulation not completed")

    result = run.result
    objective = run.config_snapshot.get("objective", "objective")

    if format == "json":
        data = {
            "run_id": run_id,
            "objective": objective,
            "seed": run.seed,
            "iterations": run.iterations,
            "engine_version": run.engine_version,
            "summary": result.summary,
            "sensitivity": result.sensitivity,
        }
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="report_{run_id[:8]}.json"'},
        )

    # CSV — flatten summary stats
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["metric", "value"])
    writer.writerow(["run_id", run_id])
    writer.writerow(["objective", objective])
    writer.writerow(["seed", run.seed])
    writer.writerow(["iterations", run.iterations])
    for k, v in result.summary.items():
        writer.writerow([k, v])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{run_id[:8]}.csv"'},
    )
