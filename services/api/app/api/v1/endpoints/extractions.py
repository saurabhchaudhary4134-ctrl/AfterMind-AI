"""LLM extraction endpoint — natural-language decision extraction with human confirmation gate."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.decision_repo import DecisionRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.services.llm import ExtractionDraft, get_llm_provider

router = APIRouter(tags=["extractions"])


class ExtractionRequest(BaseModel):
    text: str = Field(min_length=10, max_length=10000,
                      description="Natural-language description of the decision")
    max_tokens: int = Field(default=2000, ge=100, le=4000)


class ExtractionResponse(BaseModel):
    """The extraction draft — requires user confirmation before any DB write."""
    draft: ExtractionDraft
    confirmed: bool = False  # Always False — user must explicitly confirm
    confirmation_required_message: str = (
        "Review the extracted assumptions below. Confirm only what you believe is accurate. "
        "These are LLM suggestions, not verified facts."
    )


@router.post("/decisions/{decision_id}/extract", response_model=ExtractionResponse)
async def extract_decision(
    decision_id: str,
    payload: ExtractionRequest,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractionResponse:
    """Extract a structured decision draft from natural-language text.

    Returns a draft for user review. The draft is NEVER automatically applied
    to the decision — user must explicitly confirm via PUT /decisions/{id}/dna.

    Returns 503 if no LLM provider is configured (core simulation still works).
    """
    # Verify access
    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a workspace member")

    decision = DecisionRepo(db).get_by_id(decision_id, workspace_id)
    if decision is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Decision not found")

    # Get LLM provider — 503 if not configured
    try:
        provider = get_llm_provider()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM extraction is not available: {exc}",
        ) from exc

    # Run extraction
    try:
        draft = provider.extract_decision(payload.text, max_tokens=payload.max_tokens)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Extraction failed: {exc}",
        ) from exc

    return ExtractionResponse(draft=draft)


@router.post("/simulations/{run_id}/explain")
async def generate_explanation(
    run_id: str,
    workspace_id: str = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a grounded plain-language explanation for a completed simulation.

    The explanation is generated ONLY from computed statistics — no fabrication.
    Returns 503 if no LLM provider is configured.
    """
    from app.repositories.simulation_repo import SimulationRepo

    if WorkspaceRepo(db).get_membership(workspace_id, user.id) is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not a workspace member")

    run = SimulationRepo(db).get_by_id(run_id, workspace_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Simulation not found")
    if run.status != "completed" or run.result is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Simulation not completed")

    try:
        provider = get_llm_provider()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM explanation is not available: {exc}",
        ) from exc

    objective = run.config_snapshot.get("objective", "the objective")
    explanation = provider.generate_explanation(run.result.summary, objective)

    return {
        "run_id": run_id,
        "objective": objective,
        "explanation": explanation,
        "explanation_note": (
            "This explanation is based exclusively on the computed simulation statistics. "
            "It reflects model estimates from your input assumptions, not guaranteed outcomes."
        ),
    }
