"""Tests for sensitivity analysis — tornado chart data shape and correctness."""

from __future__ import annotations

import pytest

from app.simulation.schema import DecisionModel, Distribution, DistributionType, Formula, Variable
from app.simulation.sensitivity import compute_sensitivity, _get_central_value


def _const(name: str, value: float) -> Variable:
    return Variable(name=name, distribution=Distribution(
        type=DistributionType.CONSTANT, params={"value": value}
    ))


def _normal(name: str, mean: float, std: float) -> Variable:
    return Variable(name=name, distribution=Distribution(
        type=DistributionType.NORMAL, params={"mean": mean, "std": std}
    ))


class TestSensitivityShape:
    def test_returns_variables_list(self):
        model = DecisionModel(
            variables=[_const("a", 100), _const("b", 200)],
            formulas=[Formula(name="total", expression="a + b")],
            objective="total",
        )
        result = compute_sensitivity(model, iterations=100, seed=42)
        assert "variables" in result
        assert len(result["variables"]) == 2

    def test_each_variable_has_required_fields(self):
        model = DecisionModel(
            variables=[_const("a", 100)],
            formulas=[Formula(name="result", expression="a * 2")],
            objective="result",
        )
        result = compute_sensitivity(model, iterations=100, seed=42)
        for var in result["variables"]:
            assert "name" in var
            assert "label" in var
            assert "low_impact" in var
            assert "base_impact" in var
            assert "high_impact" in var
            assert "sensitivity" in var
            assert "direction" in var

    def test_sorted_by_sensitivity_descending(self):
        model = DecisionModel(
            variables=[_const("a", 100), _const("b", 10)],
            formulas=[Formula(name="total", expression="a + b")],
            objective="total",
        )
        result = compute_sensitivity(model, iterations=100, seed=42)
        sensitivities = [v["sensitivity"] for v in result["variables"]]
        assert sensitivities == sorted(sensitivities, reverse=True)

    def test_direction_positive_for_positive_formula(self):
        """When increasing a variable increases the objective, direction should be 'positive'."""
        model = DecisionModel(
            variables=[_const("a", 100)],
            formulas=[Formula(name="result", expression="a * 2")],
            objective="result",
        )
        result = compute_sensitivity(model, iterations=100, seed=42)
        assert result["variables"][0]["direction"] == "positive"

    def test_direction_negative_for_negative_formula(self):
        """When increasing a variable decreases the objective, direction should be 'negative'."""
        model = DecisionModel(
            variables=[_const("a", 100)],
            formulas=[Formula(name="result", expression="-a + 1000")],
            objective="result",
        )
        result = compute_sensitivity(model, iterations=100, seed=42)
        assert result["variables"][0]["direction"] == "negative"


class TestCentralValue:
    def test_normal_central_is_mean(self):
        d = Distribution(type=DistributionType.NORMAL, params={"mean": 50, "std": 10})
        assert _get_central_value(d) == 50.0

    def test_uniform_central_is_midpoint(self):
        d = Distribution(type=DistributionType.UNIFORM, params={"low": 10, "high": 30})
        assert _get_central_value(d) == 20.0

    def test_triangular_central_is_peak(self):
        d = Distribution(type=DistributionType.TRIANGULAR, params={"low": 0, "peak": 7, "high": 10})
        assert _get_central_value(d) == 7.0

    def test_constant_central_is_value(self):
        d = Distribution(type=DistributionType.CONSTANT, params={"value": 42})
        assert _get_central_value(d) == 42.0

    def test_beta_central_is_mean(self):
        d = Distribution(type=DistributionType.BETA, params={"alpha": 2, "beta": 8})
        assert _get_central_value(d) == pytest.approx(0.2)
