"""Tests for the Decision DNA schema validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.simulation.schema import DecisionModel, Distribution, DistributionType, Formula, Variable


class TestDistribution:
    def test_normal_valid(self):
        d = Distribution(type=DistributionType.NORMAL, params={"mean": 100, "std": 20})
        assert d.type == DistributionType.NORMAL

    def test_normal_missing_param(self):
        with pytest.raises(ValidationError):
            Distribution(type=DistributionType.NORMAL, params={"mean": 100})

    def test_normal_extra_param(self):
        with pytest.raises(ValidationError):
            Distribution(type=DistributionType.NORMAL, params={"mean": 100, "std": 20, "extra": 5})

    def test_normal_negative_std(self):
        with pytest.raises(ValidationError):
            Distribution(type=DistributionType.NORMAL, params={"mean": 100, "std": -5})

    def test_uniform_valid(self):
        d = Distribution(type=DistributionType.UNIFORM, params={"low": 10, "high": 50})
        assert d.params["low"] == 10

    def test_uniform_low_gt_high(self):
        with pytest.raises(ValidationError):
            Distribution(type=DistributionType.UNIFORM, params={"low": 50, "high": 10})

    def test_triangular_valid(self):
        d = Distribution(type=DistributionType.TRIANGULAR, params={"low": 0, "peak": 5, "high": 10})
        assert d.params["peak"] == 5

    def test_triangular_peak_outside_range(self):
        with pytest.raises(ValidationError):
            Distribution(type=DistributionType.TRIANGULAR, params={"low": 0, "peak": 15, "high": 10})

    def test_lognormal_valid(self):
        d = Distribution(type=DistributionType.LOGNORMAL, params={"mean": 1, "sigma": 0.5})
        assert d.params["sigma"] == 0.5

    def test_beta_valid(self):
        d = Distribution(type=DistributionType.BETA, params={"alpha": 2, "beta": 5})
        assert d.params["alpha"] == 2

    def test_beta_negative_param(self):
        with pytest.raises(ValidationError):
            Distribution(type=DistributionType.BETA, params={"alpha": -1, "beta": 5})

    def test_constant_valid(self):
        d = Distribution(type=DistributionType.CONSTANT, params={"value": 42})
        assert d.params["value"] == 42


class TestVariable:
    def test_valid_variable(self):
        v = Variable(name="revenue", label="Revenue", unit="$", distribution=Distribution(
            type=DistributionType.NORMAL, params={"mean": 100, "std": 20}
        ))
        assert v.name == "revenue"

    def test_invalid_name_starts_with_digit(self):
        with pytest.raises(ValidationError):
            Variable(name="1revenue", distribution=Distribution(
                type=DistributionType.CONSTANT, params={"value": 1}
            ))

    def test_invalid_name_has_special_char(self):
        with pytest.raises(ValidationError):
            Variable(name="rev-enue", distribution=Distribution(
                type=DistributionType.CONSTANT, params={"value": 1}
            ))


class TestDecisionModel:
    def _make_dist(self, value=1.0):
        return Distribution(type=DistributionType.CONSTANT, params={"value": value})

    def test_valid_model(self):
        m = DecisionModel(
            variables=[Variable(name="x", distribution=self._make_dist(5))],
            objective="x",
        )
        assert m.objective == "x"

    def test_empty_variables_rejected(self):
        with pytest.raises(ValidationError):
            DecisionModel(variables=[], objective="x")

    def test_duplicate_variable_names(self):
        with pytest.raises(ValidationError):
            DecisionModel(
                variables=[
                    Variable(name="x", distribution=self._make_dist()),
                    Variable(name="x", distribution=self._make_dist(2)),
                ],
                objective="x",
            )

    def test_objective_not_found(self):
        with pytest.raises(ValidationError):
            DecisionModel(
                variables=[Variable(name="x", distribution=self._make_dist())],
                objective="y",
            )

    def test_formula_name_clashes_with_variable(self):
        with pytest.raises(ValidationError):
            DecisionModel(
                variables=[Variable(name="x", distribution=self._make_dist())],
                formulas=[Formula(name="x", expression="1")],
                objective="x",
            )

    def test_duplicate_formula_names(self):
        with pytest.raises(ValidationError):
            DecisionModel(
                variables=[Variable(name="x", distribution=self._make_dist())],
                formulas=[
                    Formula(name="f1", expression="x + 1"),
                    Formula(name="f1", expression="x + 2"),
                ],
                objective="f1",
            )

    def test_too_many_variables(self):
        variables = [Variable(name=f"v{i}", distribution=self._make_dist()) for i in range(51)]
        with pytest.raises(ValidationError):
            DecisionModel(variables=variables, objective="v0")
