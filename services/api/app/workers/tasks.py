"""Celery task for running simulations in the background."""

from __future__ import annotations

import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_simulation_core(run_id: str) -> None:
    """Core simulation execution logic shared by Celery and sync fallback."""
    from app.db.session import SessionLocal
    from app.services.simulation_service import SimulationService

    db = SessionLocal()
    try:
        service = SimulationService(db)
        # Determine workspace from the run
        from app.repositories.simulation_repo import SimulationRepo
        run = SimulationRepo(db).get_by_id(run_id, "")
        if run is None:
            logger.error(f"Run {run_id} not found")
            return
        service._execute_sync(run_id, run.workspace_id)
    finally:
        db.close()


if celery_app is not None:

    @celery_app.task(bind=True, name="run_simulation", max_retries=2)
    def run_simulation_task(self, run_id: str) -> None:
        """Celery task: run a simulation and persist results."""
        logger.info(f"Starting simulation run {run_id}")
        try:
            _run_simulation_core(run_id)
            logger.info(f"Completed simulation run {run_id}")
        except Exception as exc:
            logger.error(f"Simulation {run_id} failed: {exc}", exc_info=True)
            raise self.retry(exc=exc, countdown=5)

else:
    # Fallback when Celery is not installed
    def run_simulation_task(run_id: str) -> None:
        """Sync fallback when Celery is unavailable."""
        _run_simulation_core(run_id)
