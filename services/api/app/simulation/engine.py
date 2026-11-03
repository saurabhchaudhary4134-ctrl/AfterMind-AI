"""Monte Carlo simulation engine — seeded sampling, formula evaluation, iteration loop.

This is the core computational engine. It:
  1. Validates the decision model.
  2. Resolves formula evaluation order (topological sort).
  3. Samples input variables from their distributions using a seeded RNG.
  4. Evaluates formulas deterministically for each iteration.
  5. Collects objective values and computes summary statistics.

NO imports from FastAPI, SQLAlchemy, Celery, or HTTP/DB code.
Only depends on numpy, the schema, the evaluator, and the statistics module.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from app.simulation.evaluator import (
    CircularDependencyError,
    FormulaError,
    evaluate_model,
    topological_sort,
)
from app.simulation.schema import DecisionModel, DistributionType
from app.simulation.sensitivity import compute_sensitivity
from app.simulation.statistics import compute_histogram, compute_summary


@dataclass
class SimulationConfig:
    """Configuration for a simulation run."""
    model: DecisionModel
    iterations: int = 10_000
    seed: int = 42
    threshold: float | None = None
    histogram_bins: int = 50
    compute_sensitivity_flag: bool = True
    sensitivity_iterations: int = 1000


@dataclass
class SimulationResult:
    """Typed result of a simulation run."""
    objective: str
    iterations: int
    seed: int
    summary: dict
    distribution_buckets: dict
    sensitivity: dict
    elapsed_seconds: float
    config_snapshot: dict = field(default_factory=dict)
    error: str | None = None


def _sample_distribution(distribution, rng: np.random.Generator, size: int) -> np.ndarray:
    """Sample an array of values from a distribution.

    Args:
        distribution: a Distribution pydantic model
        rng: numpy random Generator (seeded)
        size: number of samples

    Returns:
        1D numpy array of sampled values.
    """
    d = distribution
    p = d.params

    if d.type == DistributionType.NORMAL:
        return rng.normal(loc=p["mean"], scale=p["std"], size=size)
    if d.type == DistributionType.UNIFORM:
        return rng.uniform(low=p["low"], high=p["high"], size=size)
    if d.type == DistributionType.TRIANGULAR:
        return rng.triangular(left=p["low"], mode=p["peak"], right=p["high"], size=size)
    if d.type == DistributionType.LOGNORMAL:
        return rng.lognormal(mean=p["mean"], sigma=p["sigma"], size=size)
    if d.type == DistributionType.BETA:
        return rng.beta(a=p["alpha"], b=p["beta"], size=size)
    if d.type == DistributionType.CONSTANT:
        return np.full(size, p["value"], dtype=np.float64)

    raise FormulaError(f"Unknown distribution type: {d.type}")


def run_simulation(config: SimulationConfig) -> SimulationResult:
    """Run a Monte Carlo simulation.

    This is the main entry point for the simulation engine.

    Args:
        config: SimulationConfig with the validated model and parameters.

    Returns:
        SimulationResult with all computed statistics.

    Raises:
        FormulaError: if a formula cannot be evaluated.
        CircularDependencyError: if formulas have circular dependencies.
        ValueError: if parameters are invalid.
    """
    model = config.model
    iterations = config.iterations

    if iterations < 1:
        raise ValueError(f"Iterations must be >= 1, got {iterations}")
    if iterations > 1_000_000:
        raise ValueError(f"Iterations must be <= 1,000,000, got {iterations}")

    start_time = time.perf_counter()

    # Build formula map and resolve evaluation order
    formula_map = {f.name: f.expression for f in model.formulas}
    if model.formulas:
        topological_sort([v.name for v in model.variables], formula_map)

    # Seed the RNG for reproducibility
    rng = np.random.default_rng(config.seed)

    # Pre-sample all input variables
    sampled: dict[str, np.ndarray] = {}
    for var in model.variables:
        sampled[var.name] = _sample_distribution(var.distribution, rng, iterations)

    # Evaluate formulas for each iteration
    # For efficiency, we evaluate per-iteration if there are formulas,
    # or use vectorized operations where possible.
    objective_values = np.empty(iterations, dtype=np.float64)

    if not model.formulas:
        # No formulas — objective is a direct variable
        if model.objective not in sampled:
            raise FormulaError(
                f"Objective '{model.objective}' not found in variables or formulas"
            )
        objective_values = sampled[model.objective].copy()
    else:
        # Evaluate formulas per-iteration
        # For better performance with many iterations, we batch into chunks
        chunk_size = min(iterations, 10_000)
        evaluator_order = topological_sort([v.name for v in model.variables], formula_map)

        for chunk_start in range(0, iterations, chunk_size):
            chunk_end = min(chunk_start + chunk_size, iterations)
            for i in range(chunk_start, chunk_end):
                # Build namespace for this iteration
                ns: dict[str, float] = {}
                for var in model.variables:
                    ns[var.name] = float(sampled[var.name][i])

                # Evaluate formulas in dependency order
                for name in evaluator_order:
                    if name in formula_map:
                        ns[name] = _safe_eval(formula_map[name], ns)

                objective_values[i] = ns[model.objective]

    # Compute statistics
    summary = compute_summary(objective_values, threshold=config.threshold)
    distribution_buckets = compute_histogram(objective_values, bins=config.histogram_bins)

    # Compute sensitivity analysis
    sensitivity_result: dict = {"variables": []}
    if config.compute_sensitivity_flag:
        sensitivity_result = compute_sensitivity(
            model=model,
            iterations=config.sensitivity_iterations,
            seed=config.seed + 1,
        )

    elapsed = time.perf_counter() - start_time

    # Build config snapshot (for reproducibility)
    config_snapshot = {
        "objective": model.objective,
        "iterations": iterations,
        "seed": config.seed,
        "threshold": config.threshold,
        "variables": [v.model_dump() for v in model.variables],
        "formulas": [f.model_dump() for f in model.formulas],
        "constraints": model.constraints,
    }

    return SimulationResult(
        objective=model.objective,
        iterations=iterations,
        seed=config.seed,
        summary=summary,
        distribution_buckets=distribution_buckets,
        sensitivity=sensitivity_result,
        elapsed_seconds=elapsed,
        config_snapshot=config_snapshot,
    )


def _safe_eval(expression: str, namespace: dict[str, float]) -> float:
    """Evaluate a single formula expression safely."""
    from app.simulation.evaluator import SafeEvaluator
    evaluator = SafeEvaluator()
    return evaluator.evaluate(expression, namespace)


class SimulationEngine:
    """High-level interface for running simulations.

    Provides a clean API for the service layer to use. The engine validates
    the model before running and returns typed results.
    """

    def __init__(self) -> None:
        pass

    def validate(self, model: DecisionModel) -> None:
        """Validate a model before simulation. Raises on invalid models."""
        # Pydantic validation already runs on construction, but we also
        # check formula dependencies here.
        formula_map = {f.name: f.expression for f in model.formulas}
        if model.formulas:
            topological_sort([v.name for v in model.variables], formula_map)

    def run(self, config: SimulationConfig) -> SimulationResult:
        """Validate and run a simulation."""
        self.validate(config.model)
        return run_simulation(config)
