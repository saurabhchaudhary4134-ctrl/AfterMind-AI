"""Sensitivity analysis — tornado chart data via one-at-a-time variation.

NO imports from FastAPI, SQLAlchemy, Celery, or HTTP/DB code.
"""

from __future__ import annotations

import numpy as np

from app.simulation.evaluator import SafeEvaluator, evaluate_model, topological_sort
from app.simulation.schema import DecisionModel, DistributionType


def compute_sensitivity(
    model: DecisionModel,
    iterations: int = 1000,
    seed: int = 42,
    variation_pct: float = 0.20,
) -> dict:
    """Compute sensitivity analysis via one-at-a-time variation.

    For each input variable, we vary its distribution mean (or central value) by
    ±variation_pct while keeping all other variables at their baseline, then measure
    the impact on the objective. Results are formatted for tornado chart visualization.

    Args:
        model: The validated decision model.
        iterations: Number of Monte Carlo iterations for each sensitivity scenario.
        seed: Random seed for reproducibility.
        variation_pct: Fraction to vary each variable's central value (e.g. 0.20 = ±20%).

    Returns:
        Dict with tornado chart data:
        {
            "variables": [
                {
                    "name": "revenue",
                    "label": "Revenue",
                    "low_impact": <float>,   # objective when var is at -variation
                    "base_impact": <float>,  # objective at baseline
                    "high_impact": <float>,  # objective when var is at +variation
                    "sensitivity": <float>,  # abs(high - low) for sorting
                    "direction": "positive" | "negative"  # whether increase helps or hurts
                },
                ...
            ]
        }
    """
    rng = np.random.default_rng(seed)
    evaluator = SafeEvaluator()

    formula_map = {f.name: f.expression for f in model.formulas}
    eval_order = topological_sort([v.name for v in model.variables], formula_map)

    # Compute baseline objective (with all variables at their mean/central value)
    baseline_values: dict[str, float] = {}
    for var in model.variables:
        baseline_values[var.name] = _get_central_value(var.distribution)

    baseline_namespace = evaluate_model(baseline_values, formula_map)
    base_objective = baseline_namespace[model.objective]

    results: list[dict] = []
    for var in model.variables:
        base_val = baseline_values[var.name]

        # Vary this variable's central value by ±variation_pct
        low_val = base_val * (1.0 - variation_pct) if base_val != 0 else -variation_pct
        high_val = base_val * (1.0 + variation_pct) if base_val != 0 else variation_pct

        # Evaluate with low and high values
        low_namespace = evaluate_model({**baseline_values, var.name: low_val}, formula_map)
        high_namespace = evaluate_model({**baseline_values, var.name: high_val}, formula_map)

        low_obj = low_namespace[model.objective]
        high_obj = high_namespace[model.objective]

        sensitivity = abs(high_obj - low_obj)
        direction = "positive" if high_obj > low_obj else "negative"

        results.append({
            "name": var.name,
            "label": var.label or var.name,
            "unit": var.unit,
            "low_impact": float(low_obj),
            "base_impact": float(base_objective),
            "high_impact": float(high_obj),
            "sensitivity": float(sensitivity),
            "direction": direction,
            "variation_pct": variation_pct,
        })

    # Sort by sensitivity (largest impact first) for tornado chart ordering
    results.sort(key=lambda x: x["sensitivity"], reverse=True)

    return {"variables": results}


def _get_central_value(distribution) -> float:
    """Get the central/expected value of a distribution for baseline calculations."""
    d = distribution
    params = d.params

    if d.type == DistributionType.NORMAL:
        return float(params["mean"])
    if d.type == DistributionType.UNIFORM:
        return float((params["low"] + params["high"]) / 2)
    if d.type == DistributionType.TRIANGULAR:
        return float(params["peak"])
    if d.type == DistributionType.LOGNORMAL:
        return float(params["mean"])
    if d.type == DistributionType.BETA:
        a, b = params["alpha"], params["beta"]
        return float(a / (a + b))
    if d.type == DistributionType.CONSTANT:
        return float(params["value"])
    return 0.0
