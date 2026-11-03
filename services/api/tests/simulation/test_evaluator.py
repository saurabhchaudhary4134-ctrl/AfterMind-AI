"""Tests for the safe formula evaluator — security, correctness, dependencies."""

from __future__ import annotations

import pytest

from app.simulation.evaluator import (
    CircularDependencyError,
    FormulaError,
    SafeEvaluator,
    evaluate_model,
    extract_references,
    topological_sort,
)


class TestSafeEvaluation:
    def test_simple_arithmetic(self):
        e = SafeEvaluator()
        assert e.evaluate("2 + 3", {}) == 5.0
        assert e.evaluate("10 - 4", {}) == 6.0
        assert e.evaluate("3 * 4", {}) == 12.0
        assert e.evaluate("10 / 4", {}) == 2.5
        assert e.evaluate("2 ** 3", {}) == 8.0
        assert e.evaluate("10 % 3", {}) == 1.0

    def test_parentheses(self):
        e = SafeEvaluator()
        assert e.evaluate("(2 + 3) * 4", {}) == 20.0
        assert e.evaluate("2 + (3 * 4)", {}) == 14.0

    def test_unary_minus(self):
        e = SafeEvaluator()
        assert e.evaluate("-5", {}) == -5.0
        assert e.evaluate("-5 + 10", {}) == 5.0

    def test_variable_substitution(self):
        e = SafeEvaluator()
        assert e.evaluate("revenue * margin", {"revenue": 1000, "margin": 0.2}) == 200.0

    def test_complex_expression(self):
        e = SafeEvaluator()
        ns = {"revenue": 1000, "costs": 300, "tax_rate": 0.25}
        result = e.evaluate("(revenue - costs) * (1 - tax_rate)", ns)
        assert result == pytest.approx(525.0)

    def test_division_by_zero_raises(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="Division by zero"):
            e.evaluate("1 / 0", {})


class TestSecurity:
    """Malicious inputs must be rejected."""

    def test_blocked_import(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="blocked|disallowed"):
            e.evaluate("__import__('os')", {})

    def test_blocked_eval(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="disallowed"):
            e.evaluate("eval('1+1')", {})

    def test_blocked_os_system(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="blocked|disallowed"):
            e.evaluate("os.system('rm -rf /')", {})

    def test_no_attribute_access(self):
        e = SafeEvaluator()
        # __class__.__bases__ should be blocked
        with pytest.raises(FormulaError, match="blocked"):
            e.evaluate("__class__.__bases__", {})

    def test_empty_expression(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="empty"):
            e.evaluate("", {})

    def test_undefined_variable(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="undefined"):
            e.evaluate("unknown_var + 1", {"x": 5})

    def test_disallowed_characters(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="disallowed"):
            e.evaluate("x; import os", {"x": 5})

    def test_too_long_expression(self):
        e = SafeEvaluator()
        with pytest.raises(FormulaError, match="maximum length"):
            e.evaluate("1" + " + 1" * 600, {})

    def test_no_subscript(self):
        e = SafeEvaluator()
        # Subscript access should be blocked by character filter
        with pytest.raises(FormulaError):
            e.evaluate("__builtins__['eval']", {})


class TestTopologicalSort:
    def test_no_dependencies(self):
        order = topological_sort(["a", "b", "c"], {})
        assert set(order) == {"a", "b", "c"}

    def test_linear_dependency(self):
        order = topological_sort(["a"], {"b": "a + 1", "c": "b + 1"})
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_circular_dependency_detected(self):
        with pytest.raises(CircularDependencyError):
            topological_sort([], {"a": "b + 1", "b": "a + 1"})

    def test_three_way_circular(self):
        with pytest.raises(CircularDependencyError):
            topological_sort([], {"a": "b + 1", "b": "c + 1", "c": "a + 1"})

    def test_formula_references_undefined(self):
        with pytest.raises(FormulaError, match="undefined"):
            topological_sort(["x"], {"f": "x + y"})


class TestEvaluateModel:
    def test_evaluate_no_formulas(self):
        result = evaluate_model({"x": 10, "y": 20}, {})
        assert result["x"] == 10
        assert result["y"] == 20

    def test_evaluate_with_formulas(self):
        result = evaluate_model(
            {"revenue": 1000, "costs": 300},
            {"profit": "revenue - costs", "margin": "profit / revenue"},
        )
        assert result["profit"] == 700.0
        assert result["margin"] == 0.7

    def test_evaluate_chain(self):
        result = evaluate_model(
            {"a": 10},
            {"b": "a * 2", "c": "b + 5", "d": "c ** 2"},
        )
        assert result["b"] == 20.0
        assert result["c"] == 25.0
        assert result["d"] == 625.0

    def test_evaluate_circular_raises(self):
        with pytest.raises(CircularDependencyError):
            evaluate_model({}, {"a": "b", "b": "a"})

    def test_extract_references(self):
        refs = extract_references("revenue * margin - costs")
        assert refs == {"revenue", "margin", "costs"}

    def test_extract_references_blocks_dunder(self):
        refs = extract_references("__import__ + x")
        assert "__import__" not in refs
        assert "x" in refs
