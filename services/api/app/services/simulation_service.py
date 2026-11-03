"""Simulation service — orchestrates run creation, execution, and result persistence.

In production: dispatches to Celery workers via Redis.
In dev (SIMULATION_SYNC=true): runs inline in the request thread.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories.decision_repo import DecisionRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.simulation_repo import SimulationRepo
from app.repositories.workspace_repo import WorkspaceRepo
from app.simulation import ENGINE_VERSION
from app.simulation.engine import SimulationConfig, SimulationEngine
from app.simulation.schema import DecisionModel

logger = logging.getLogger(__name__)


class SimulationError(Exception):
    """Raised when simulation setup or execution fails."""


class SimulationService:
    """Orchestrates the full simulation lifecycle."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.run_repo = SimulationRepo(db)
        self.scenario_repo = ScenarioRepo(db)
        self.decision_repo = DecisionRepo(db)
        self.workspace_repo = WorkspaceRepo(db)
        self.engine = SimulationEngine()

    def create_run(
        self,
        workspace_id: str,
        decision_id: str,
        scenario_id: str,
        user_id: str,
        iterations: int = 10_000,
        seed: int | None = None,
        threshold: float | None = None,
        model_config_override: dict | None = None,
    ) -> str:
        """Create a simulation run and dispatch it. Returns the run ID."""
        # Verify workspace membership
        if self.workspace_repo.get_membership(workspace_id, user_id) is None:
            raise SimulationError("Not a workspace member")

        # Verify decision belongs to workspace
        decision = self.decision_repo.get_by_id(decision_id, workspace_id)
        if decision is None:
            raise SimulationError("Decision not found")

        if decision.current_version_id is None:
            raise SimulationError("Decision has no DNA version. Update the DNA first.")

        # Verify scenario belongs to the decision + workspace
        scenario = self.scenario_repo.get_by_id(scenario_id, workspace_id)
        if scenario is None:
            raise SimulationError("Scenario not found")
        if scenario.decision_id != decision_id:
            raise SimulationError("Scenario does not belong to this decision")

        # Validate iterations
        if iterations < 1 or iterations > settings.MAX_ITERATIONS:
            raise SimulationError(
                f"Iterations must be between 1 and {settings.MAX_ITERATIONS}"
            )

        # Generate seed if not provided
        actual_seed = seed if seed is not None else random.randint(0, 2**31 - 1)

        # Build config snapshot (immutable)
        version = self.decision_repo.get_latest_version_number(decision_id)
        latest_version = self.decision_repo.get_version(decision_id, workspace_id, version)
        decision_dna = latest_version.decision_dna if latest_version else {}

        config_snapshot = {
            "decision_dna": decision_dna,
            "scenario_overrides": scenario.assumption_overrides,
            "model_config_override": model_config_override or {},
            "threshold": threshold,
        }

        # Create the run record
        run = self.run_repo.create(
            scenario_id=scenario_id,
            decision_id=decision_id,
            workspace_id=workspace_id,
            status="queued",
            iterations=iterations,
            seed=actual_seed,
            engine_version=ENGINE_VERSION,
            config_snapshot=config_snapshot,
            requested_by=user_id,
        )
        self.db.commit()

        # Dispatch
        if settings.SIMULATION_SYNC:
            # Run synchronously (dev mode)
            self._execute_sync(run.id, workspace_id)
        else:
            # Dispatch to Celery
            try:
                from app.workers.tasks import run_simulation_task
                run_simulation_task.delay(run.id)
            except Exception as exc:
                logger.warning(f"Celery dispatch failed, falling back to sync: {exc}")
                self._execute_sync(run.id, workspace_id)

        return run.id

    def _execute_sync(self, run_id: str, workspace_id: str) -> None:
        """Execute a simulation synchronously and persist results."""
        run = self.run_repo.get_by_id(run_id, workspace_id)
        if run is None:
            raise SimulationError("Run not found")
        if run.status == "completed":
            return  # Idempotent: already done

        self.run_repo.update_status(run, "running", progress=0)
        self.db.commit()

        try:
            # Reconstruct the DecisionModel from the stored DNA + overrides
            snapshot = run.config_snapshot
            dna = snapshot.get("decision_dna", {})
            overrides = snapshot.get("scenario_overrides", {})
            threshold = snapshot.get("threshold")

            # Apply scenario overrides to the DNA
            merged_dna = self._apply_overrides(dna, overrides)

            model = DecisionModel.model_validate(merged_dna)

            config = SimulationConfig(
                model=model,
                iterations=run.iterations,
                seed=run.seed,
                threshold=threshold,
            )

            self.run_repo.update_status(run, "running", progress=50)
            self.db.commit()

            result = self.engine.run(config)

            # Persist results
            self.run_repo.create_result(
                run_id=run_id,
                summary=result.summary,
                distribution_buckets=result.distribution_buckets,
                sensitivity=result.sensitivity,
            )

            # Store config snapshot from the engine for full reproducibility
            run.config_snapshot.update(result.config_snapshot)

            # SQLAlchemy doesn't detect in-place JSON mutations — flag it manually
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(run, "config_snapshot")

            self.run_repo.update_status(run, "completed", progress=100)
            self.db.commit()

        except Exception as exc:
            logger.error(f"Simulation {run_id} failed: {exc}", exc_info=True)
            self.run_repo.update_status(run, "failed", error_message=str(exc))
            self.db.commit()
            raise

    def cancel_run(self, run_id: str, workspace_id: str) -> bool:
        """Cancel a queued or running simulation."""
        run = self.run_repo.get_by_id(run_id, workspace_id)
        if run is None:
            return False
        if run.status in ("completed", "failed", "cancelled"):
            return False
        self.run_repo.update_status(run, "cancelled")
        self.db.commit()
        return True

    def get_run(self, run_id: str, workspace_id: str) -> dict | None:
        """Get run status. Returns None if not found."""
        run = self.run_repo.get_by_id(run_id, workspace_id)
        if run is None:
            return None
        return run

    def get_result(self, run_id: str, workspace_id: str) -> dict | None:
        """Get simulation results. Returns None if not found or not completed."""
        result = self.run_repo.get_result(run_id, workspace_id)
        if result is None:
            return None
        return result

    @staticmethod
    def _apply_overrides(dna: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
        """Apply scenario assumption overrides to the decision DNA.

        Overrides can replace entire variables or specific distribution parameters.
        """
        if not overrides:
            return dna

        merged = json.loads(json.dumps(dna))  # deep copy

        # Override individual variables
        variables = merged.get("variables", [])
        for var in variables:
            var_name = var.get("name")
            if var_name in overrides:
                var_override = overrides[var_name]
                if isinstance(var_override, dict):
                    # Could be distribution params override
                    if "distribution" in var_override:
                        var["distribution"] = var_override["distribution"]
                    elif "params" in var_override:
                        var.setdefault("distribution", {})["params"] = var_override["params"]
                    # Override any other field
                    for k, v in var_override.items():
                        if k not in ("distribution", "params"):
                            var[k] = v

        # Override formulas
        formulas = merged.get("formulas", [])
        for formula in formulas:
            f_name = formula.get("name")
            if f_name in overrides:
                f_override = overrides[f_name]
                if isinstance(f_override, str):
                    formula["expression"] = f_override

        return merged
