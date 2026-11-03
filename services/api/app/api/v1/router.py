"""Aggregated v1 API router — includes all endpoint modules."""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, decisions, extractions, health, outcomes, scenarios, simulations, users, workspaces

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workspaces.router)
api_router.include_router(decisions.router)
api_router.include_router(scenarios.router)
api_router.include_router(simulations.router)
api_router.include_router(outcomes.router)
api_router.include_router(extractions.router)
