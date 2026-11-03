"""Mock LLM provider — deterministic responses for testing and offline development."""

from __future__ import annotations

import re
from typing import Any

from app.services.llm.base import (
    ExtractionDraft,
    ExtractedFormula,
    ExtractedVariable,
    LLMProvider,
)


class MockLLMProvider(LLMProvider):
    """Deterministic mock provider — useful for tests and offline dev.

    Parses obvious patterns (numbers, common business terms) from the input text.
    """

    @property
    def name(self) -> str:
        return "mock"

    def is_available(self) -> bool:
        return True

    def extract_decision(self, text: str, max_tokens: int = 2000) -> ExtractionDraft:
        """Extract a simple structured draft by parsing obvious patterns."""
        words = text.lower()

        # Detect common financial variables
        variables: list[ExtractedVariable] = []
        formulas: list[ExtractedFormula] = []
        missing: list[str] = []

        # Simple keyword → variable suggestions
        _TERM_MAP = [
            ("revenue", "revenue", "$", "normal", {"mean": 100000, "std": 20000}),
            ("sales", "sales", "$", "normal", {"mean": 100000, "std": 20000}),
            ("cost", "costs", "$", "normal", {"mean": 60000, "std": 10000}),
            ("expense", "expenses", "$", "normal", {"mean": 60000, "std": 10000}),
            ("price", "price", "$", "uniform", {"low": 10, "high": 100}),
            ("demand", "demand", "units", "normal", {"mean": 1000, "std": 200}),
            ("growth", "growth_rate", "%", "triangular", {"low": 0.0, "peak": 0.1, "high": 0.3}),
            ("margin", "margin", "%", "uniform", {"low": 0.1, "high": 0.4}),
            ("probability", "probability", "prob", "uniform", {"low": 0.3, "high": 0.8}),
            ("risk", "risk_factor", "", "beta", {"alpha": 2, "beta": 5}),
        ]

        seen_names: set[str] = set()
        for keyword, name, unit, dist_type, params in _TERM_MAP:
            if keyword in words and name not in seen_names:
                variables.append(ExtractedVariable(
                    name=name,
                    label=name.replace("_", " ").title(),
                    unit=unit,
                    distribution_type=dist_type,
                    distribution_params=params,
                    confidence=0.6,
                    source_text=f"Detected '{keyword}' in input text",
                ))
                seen_names.add(name)

        # If we got revenue and costs, suggest a profit formula
        var_names = {v.name for v in variables}
        if "revenue" in var_names and "costs" in var_names:
            formulas.append(ExtractedFormula(
                name="profit",
                expression="revenue - costs",
                description="Profit = Revenue - Costs",
                confidence=0.9,
            ))
        elif "revenue" in var_names and "expenses" in var_names:
            formulas.append(ExtractedFormula(
                name="profit",
                expression="revenue - expenses",
                description="Profit = Revenue - Expenses",
                confidence=0.9,
            ))
        elif "price" in var_names and "demand" in var_names:
            formulas.append(ExtractedFormula(
                name="revenue",
                expression="price * demand",
                description="Revenue = Price × Demand",
                confidence=0.85,
            ))

        # Flag obvious missing assumptions
        if not variables:
            missing.append("No quantifiable variables detected — please describe specific metrics with ranges.")
        if not formulas and len(variables) > 1:
            missing.append("No formula linking variables to an outcome was detected — describe how variables combine.")

        # Use first formula name or first variable as objective
        if formulas:
            objective = formulas[0].name
        elif variables:
            objective = variables[0].name
        else:
            objective = ""

        # Extract a title from the first sentence
        title = text.split(".")[0].strip()[:200] if text else "Untitled Decision"

        return ExtractionDraft(
            title=title,
            description=text[:500],
            objective=objective,
            suggested_variables=variables,
            suggested_formulas=formulas,
            missing_assumptions=missing,
            confidence=0.65 if variables else 0.2,
            provider=self.name,
            model="mock-v1",
            requires_confirmation=True,
        )

    def generate_explanation(self, run_summary: dict[str, Any], objective: str) -> str:
        """Generate a grounded explanation from computed statistics only."""
        mean = run_summary.get("mean", 0)
        std = run_summary.get("std", 0)
        p5 = run_summary.get("p5", 0)
        p95 = run_summary.get("p95", 0)
        n = run_summary.get("n", 0)

        return (
            f"Based on {n:,} simulation iterations, the '{objective}' has a mean of "
            f"{mean:.2f} with a standard deviation of {std:.2f}. "
            f"There is a 90% probability that the outcome will fall between "
            f"{p5:.2f} (P5) and {p95:.2f} (P95). "
            "These results are based entirely on the model inputs and assumptions you provided; "
            "they represent simulated estimates, not guaranteed outcomes."
        )
