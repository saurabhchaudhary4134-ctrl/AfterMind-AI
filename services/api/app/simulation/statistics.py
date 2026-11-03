"""Statistical computations for Monte Carlo simulation results.

NO imports from FastAPI, SQLAlchemy, Celery, or HTTP/DB code.
"""

from __future__ import annotations

import math

import numpy as np


def compute_percentiles(values: np.ndarray, percentiles: list[float] | None = None) -> dict[str, float]:
    """Compute named percentile values for the given array.

    Args:
        values: 1D array of simulation outcomes.
        percentiles: list of percentile values (0-100). Defaults to
            [5, 10, 25, 50, 75, 90, 95].

    Returns:
        Dict mapping "p5", "p10", etc. → float values.
    """
    if percentiles is None:
        percentiles = [5, 10, 25, 50, 75, 90, 95]

    result: dict[str, float] = {}
    for p in percentiles:
        result[f"p{int(p)}"] = float(np.percentile(values, p))
    return result


def compute_summary(values: np.ndarray, threshold: float | None = None) -> dict:
    """Compute full summary statistics for a simulation outcome array.

    Includes percentiles, mean, std, skewness, kurtosis, threshold probabilities,
    CVaR, and downside risk metrics.

    Args:
        values: 1D array of simulation outcomes.
        threshold: optional threshold for probability calculations.

    Returns:
        Dict with all computed statistics.
    """
    values = np.asarray(values, dtype=np.float64)
    n = len(values)

    percentiles = compute_percentiles(values)

    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if n > 1 else 0.0
    variance = float(np.var(values, ddof=1)) if n > 1 else 0.0
    min_val = float(np.min(values))
    max_val = float(np.max(values))

    summary: dict = {
        "n": n,
        "mean": mean,
        "std": std,
        "variance": variance,
        "min": min_val,
        "max": max_val,
        "range": max_val - min_val,
        **percentiles,
    }

    # Skewness and kurtosis (only meaningful with enough samples)
    if n > 2:
        summary["skewness"] = float(_skewness(values))
    if n > 3:
        summary["kurtosis"] = float(_kurtosis(values))

    # Coefficient of variation
    if mean != 0 and std > 0:
        summary["cv"] = std / abs(mean)
    else:
        summary["cv"] = 0.0

    # CVaR (Conditional Value at Risk) at the 5th percentile
    p5 = percentiles["p5"]
    tail = values[values <= p5]
    summary["cvar_5"] = float(np.mean(tail)) if len(tail) > 0 else float(p5)

    # Threshold probabilities
    if threshold is not None:
        summary["prob_at_least"] = float(np.mean(values >= threshold))
        summary["prob_at_most"] = float(np.mean(values <= threshold))
        summary["prob_exceeds"] = float(np.mean(values > threshold))

        # Downside risk: probability and expected magnitude of being below threshold
        below = values[values < threshold]
        summary["prob_below_threshold"] = float(len(below) / n) if n > 0 else 0.0
        summary["expected_shortfall"] = float(np.mean(below)) if len(below) > 0 else 0.0
        summary["downside_deviation"] = (
            float(math.sqrt(np.mean(np.minimum(threshold - values, 0) ** 2))) if n > 0 else 0.0
        )

    return summary


def compute_histogram(
    values: np.ndarray, bins: int = 50
) -> dict:
    """Compute histogram bucket data for visualization.

    Returns a dict with bin edges and counts suitable for charting.
    """
    values = np.asarray(values, dtype=np.float64)
    counts, edges = np.histogram(values, bins=bins)
    return {
        "bin_edges": [float(e) for e in edges],
        "bin_centers": [float((edges[i] + edges[i + 1]) / 2) for i in range(len(edges) - 1)],
        "counts": [int(c) for c in counts],
        "bins": bins,
    }


def _skewness(values: np.ndarray) -> float:
    """Compute sample skewness (Fisher-Pearson)."""
    n = len(values)
    mean = np.mean(values)
    std = np.std(values, ddof=1)
    if std == 0:
        return 0.0
    return float(np.sum(((values - mean) / std) ** 3) * n / ((n - 1) * (n - 2)))


def _kurtosis(values: np.ndarray) -> float:
    """Compute excess kurtosis."""
    n = len(values)
    mean = np.mean(values)
    std = np.std(values, ddof=1)
    if std == 0:
        return 0.0
    k2 = np.sum(((values - mean) / std) ** 4)
    return float(k2 * n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))
                - 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
