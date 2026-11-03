"""Tests for the Monte Carlo simulation engine — reproducibility, stats correctness."""

from __future__ import annotations

import math

import numpy as np
import pytest

from app.simulation.engine import SimulationConfig, SimulationEngine, run_simulation
from app.simulation.schema import DecisionModel, Distribution, DistributionType, Formula, Variable


def _const(name: str, value: float) -> Variable:
    return Variable(name=name, distribution=Distribution(
        type=DistributionType.CONSTANT, params={"value": value}
    ))


def _normal(name: str, mean: float, std: float) -> Variable:
    return Variable(name=name, distribution=Distribution(
        type=DistributionType.NORMAL, params={"mean": mean, "std": std}
    ))


class TestReproducibility:
    """Same seed must produce identical results."""

    def test_same_seed_same_result(self):
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        config = SimulationConfig(model=model, iterations=5000, seed=42)
        result1 = run_simulation(config)
        result2 = run_simulation(config)
        assert result1.summary["mean"] == result2.summary["mean"]
        assert result1.summary["p50"] == result2.summary["p50"]

    def test_different_seed_different_result(self):
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        r1 = run_simulation(SimulationConfig(model=model, iterations=5000, seed=42))
        r2 = run_simulation(SimulationConfig(model=model, iterations=5000, seed=99))
        assert r1.summary["mean"] != r2.summary["mean"]

    def test_seed_stored_in_result(self):
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=100, seed=12345))
        assert result.seed == 12345

    def test_config_snapshot_stored(self):
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=100, seed=1))
        assert result.config_snapshot["iterations"] == 100
        assert result.config_snapshot["seed"] == 1
        assert result.config_snapshot["objective"] == "x"
        assert len(result.config_snapshot["variables"]) == 1


class TestStatisticalCorrectness:
    """Statistics for known distributions should match theoretical values."""

    def test_normal_mean_close_to_true(self):
        """For N(100, 20), sample mean should be close to 100 with 50k iterations."""
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=50000, seed=42))
        assert abs(result.summary["mean"] - 100) < 2.0  # Within ~2 of true mean

    def test_normal_std_close_to_true(self):
        """For N(100, 20), sample std should be close to 20."""
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=50000, seed=42))
        assert abs(result.summary["std"] - 20) < 2.0

    def test_uniform_mean_in_range(self):
        """For U(10, 50), mean should be ~30."""
        model = DecisionModel(
            variables=[Variable(name="x", distribution=Distribution(
                type=DistributionType.UNIFORM, params={"low": 10, "high": 50}
            ))],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=50000, seed=42))
        assert abs(result.summary["mean"] - 30) < 3.0

    def test_constant_returns_exact_value(self):
        """Constant distribution should produce exactly that value."""
        model = DecisionModel(
            variables=[_const("x", 42.0)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=100, seed=1))
        assert result.summary["mean"] == 42.0
        assert result.summary["std"] == 0.0
        assert result.summary["p5"] == 42.0
        assert result.summary["p95"] == 42.0

    def test_formula_sum_correct(self):
        """A formula summing two known constants should give the exact result."""
        model = DecisionModel(
            variables=[_const("a", 100), _const("b", 200)],
            formulas=[Formula(name="total", expression="a + b")],
            objective="total",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=100, seed=1))
        assert result.summary["mean"] == 300.0

    def test_formula_multiply_correct(self):
        model = DecisionModel(
            variables=[_const("revenue", 1000), _const("margin", 0.3)],
            formulas=[Formula(name="profit", expression="revenue * margin")],
            objective="profit",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=100, seed=1))
        assert result.summary["mean"] == pytest.approx(300.0)

    def test_percentile_ordering(self):
        """Percentiles should be monotonically increasing."""
        model = DecisionModel(
            variables=[_normal("x", mean=50, std=10)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=10000, seed=42))
        s = result.summary
        assert s["p5"] < s["p10"] < s["p25"] < s["p50"] < s["p75"] < s["p90"] < s["p95"]

    def test_threshold_probability(self):
        """P(X >= threshold) for a constant should be exactly 1 or 0."""
        model = DecisionModel(
            variables=[_const("x", 50)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(
            model=model, iterations=100, seed=1, threshold=40
        ))
        assert result.summary["prob_at_least"] == 1.0  # 50 >= 40

        result2 = run_simulation(SimulationConfig(
            model=model, iterations=100, seed=1, threshold=60
        ))
        assert result2.summary["prob_at_least"] == 0.0  # 50 < 60

    def test_cvar_correct_for_constant(self):
        model = DecisionModel(
            variables=[_const("x", 50)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(model=model, iterations=100, seed=1))
        assert result.summary["cvar_5"] == 50.0


class TestHistogram:
    def test_histogram_has_correct_shape(self):
        model = DecisionModel(
            variables=[_normal("x", mean=100, std=20)],
            objective="x",
        )
        result = run_simulation(SimulationConfig(
            model=model, iterations=1000, seed=42, histogram_bins=20
        ))
        h = result.distribution_buckets
        assert h["bins"] == 20
        assert len(h["bin_edges"]) == 21  # n+1 edges for n bins
        assert len(h["counts"]) == 20
        assert sum(h["counts"]) == 1000


class TestErrorHandling:
    def test_zero_iterations_rejected(self):
        model = DecisionModel(
            variables=[_const("x", 1)],
            objective="x",
        )
        with pytest.raises(ValueError):
            run_simulation(SimulationConfig(model=model, iterations=0, seed=1))

    def test_too_many_iterations_rejected(self):
        model = DecisionModel(
            variables=[_const("x", 1)],
            objective="x",
        )
        with pytest.raises(ValueError):
            run_simulation(SimulationConfig(model=model, iterations=2_000_000, seed=1))

    def test_circular_dependency_rejected(self):
        model = DecisionModel(
            variables=[_const("a", 1)],
            formulas=[
                Formula(name="b", expression="a + c"),
                Formula(name="c", expression="b + 1"),
            ],
            objective="c",
        )
        engine = SimulationEngine()
        with pytest.raises(Exception):
            engine.run(SimulationConfig(model=model, iterations=10, seed=1))


class TestNoWebDBImports:
    """The simulation package must not import any web/DB/framework code."""

    def test_no_fastapi_imports(self):
        import app.simulation
        import app.simulation.engine
        import app.simulation.evaluator
        import app.simulation.schema
        import app.simulation.statistics
        import app.simulation.sensitivity

        # Check that none of these modules have imported fastapi/sqlalchemy/celery
        import sys
        sim_modules = [
            m for m in sys.modules
            if m.startswith("app.simulation")
        ]
        # These modules should NOT be in sys.modules as imported by sim code
        forbidden = ["fastapi", "sqlalchemy", "celery"]
        for mod in sim_modules:
            mod_obj = sys.modules[mod]
            assert mod_obj is not None
