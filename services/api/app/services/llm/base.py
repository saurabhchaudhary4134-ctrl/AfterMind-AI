"""LLM provider abstraction — defines the interface all providers must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.simulation.schema import Variable, Formula, Distribution, DistributionType


class ExtractedVariable(BaseModel):
    """A variable extracted from natural language by an LLM, awaiting user confirmation."""

    model_config = ConfigDict(extra="ignore")

    name: str
    label: str
    unit: str = ""
    distribution_type: str = "normal"
    distribution_params: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    source_text: str = ""  # The original text fragment that suggested this variable


class ExtractedFormula(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    expression: str
    description: str = ""
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class ExtractionDraft(BaseModel):
    """A structured draft extracted from natural language.

    This is NEVER written to the database without explicit user confirmation.
    All fields are clearly labeled as 'suggested' not validated facts.
    """

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    description: str = ""
    objective: str = ""
    suggested_variables: list[ExtractedVariable] = Field(default_factory=list)
    suggested_formulas: list[ExtractedFormula] = Field(default_factory=list)
    missing_assumptions: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    provider: str = ""
    model: str = ""
    requires_confirmation: bool = True  # Always True — LLM drafts require human confirmation

    def to_decision_dna(self) -> dict:
        """Convert the draft to a Decision DNA dict for user review.

        The result is a SUGGESTION only — never auto-applied to a decision.
        """
        variables = []
        for v in self.suggested_variables:
            # Only include variables with recognizable distribution types
            dist_type = v.distribution_type.lower()
            if dist_type not in [dt.value for dt in DistributionType]:
                dist_type = "normal"
            variables.append({
                "name": v.name,
                "label": v.label,
                "unit": v.unit,
                "distribution": {
                    "type": dist_type,
                    "params": v.distribution_params or {"mean": 0, "std": 1},
                },
            })
        formulas = [
            {"name": f.name, "expression": f.expression, "description": f.description}
            for f in self.suggested_formulas
        ]
        return {
            "variables": variables,
            "formulas": formulas,
            "objective": self.suggested_formulas[0].name if self.suggested_formulas else (
                variables[0]["name"] if variables else ""
            ),
            "constraints": [],
        }


class LLMProvider(ABC):
    """Abstract LLM provider interface."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g. 'openai', 'mock')."""

    @abstractmethod
    def extract_decision(self, text: str, max_tokens: int = 2000) -> ExtractionDraft:
        """Extract a structured decision draft from natural-language text.

        Returns a validated ExtractionDraft. Never writes to the database.
        LLM output is untrusted and must be confirmed by the user before use.
        """

    @abstractmethod
    def generate_explanation(self, run_summary: dict[str, Any], objective: str) -> str:
        """Generate a plain-language explanation based ONLY on computed statistics.

        The explanation must reference actual computed values only.
        It must never fabricate data or claim facts not present in run_summary.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this provider is configured and reachable."""
