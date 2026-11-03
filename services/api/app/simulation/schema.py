"""Decision DNA schema — the typed, validated structured representation of a decision model.

This module defines the core data structures for the simulation engine. All
validation happens here so the engine can trust its inputs.

NO imports from FastAPI, SQLAlchemy, Celery, or HTTP/DB code.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Valid identifier pattern: letters, digits, underscores, not starting with digit
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Maximum model complexity
MAX_VARIABLES = 50
MAX_FORMULAS = 50
MAX_NAME_LENGTH = 100
MAX_EXPRESSION_LENGTH = 1000


class DistributionType(str, Enum):
    """Supported probability distribution types."""

    NORMAL = "normal"
    UNIFORM = "uniform"
    TRIANGULAR = "triangular"
    LOGNORMAL = "lognormal"
    BETA = "beta"
    CONSTANT = "constant"


# Required and optional parameters per distribution type
_DISTRIBUTION_PARAMS: dict[DistributionType, set[str]] = {
    DistributionType.NORMAL: {"mean", "std"},
    DistributionType.UNIFORM: {"low", "high"},
    DistributionType.TRIANGULAR: {"low", "peak", "high"},
    DistributionType.LOGNORMAL: {"mean", "sigma"},
    DistributionType.BETA: {"alpha", "beta"},
    DistributionType.CONSTANT: {"value"},
}


class Distribution(BaseModel):
    """A probability distribution with type-specific parameter validation."""

    model_config = ConfigDict(extra="forbid")

    type: DistributionType
    params: dict[str, float]

    @field_validator("params")
    @classmethod
    def validate_params(cls, v: dict[str, float], info) -> dict[str, float]:
        if not info.data or "type" not in info.data:
            return v
        dist_type = info.data["type"]
        required = _DISTRIBUTION_PARAMS.get(dist_type, set())
        missing = required - set(v.keys())
        if missing:
            raise ValueError(
                f"Distribution '{dist_type.value}' requires params: {sorted(required)}. "
                f"Missing: {sorted(missing)}"
            )
        extra = set(v.keys()) - required
        if extra:
            raise ValueError(
                f"Distribution '{dist_type.value}' does not accept params: {sorted(extra)}"
            )

        # Validate numeric ranges per distribution type
        if dist_type == DistributionType.NORMAL and v["std"] < 0:
            raise ValueError("Normal distribution std must be >= 0")
        if dist_type == DistributionType.UNIFORM and v["low"] > v["high"]:
            raise ValueError("Uniform distribution low must be <= high")
        if dist_type == DistributionType.TRIANGULAR:
            if not (v["low"] <= v["peak"] <= v["high"]):
                raise ValueError("Triangular: low <= peak <= high required")
        if dist_type == DistributionType.LOGNORMAL and v["sigma"] < 0:
            raise ValueError("Lognormal sigma must be >= 0")
        if dist_type == DistributionType.BETA:
            if v["alpha"] <= 0 or v["beta"] <= 0:
                raise ValueError("Beta alpha and beta must be > 0")

        return v


class Variable(BaseModel):
    """An input variable with a name, label, unit, and probability distribution."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=MAX_NAME_LENGTH)
    label: str = Field(default="", max_length=200)
    unit: str = Field(default="", max_length=50)
    distribution: Distribution

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _IDENTIFIER_RE.match(v):
            raise ValueError(
                f"Variable name '{v}' is not a valid identifier "
                f"(letters, digits, underscores; cannot start with a digit)"
            )
        return v


class Formula(BaseModel):
    """A deterministic formula linking variables to an output variable."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(max_length=MAX_NAME_LENGTH)
    expression: str = Field(max_length=MAX_EXPRESSION_LENGTH)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not _IDENTIFIER_RE.match(v):
            raise ValueError(f"Formula name '{v}' is not a valid identifier")
        return v


class DecisionModel(BaseModel):
    """The complete Decision DNA: variables, formulas, objective, and constraints."""

    model_config = ConfigDict(extra="forbid")

    variables: list[Variable] = Field(min_length=1, max_length=MAX_VARIABLES)
    formulas: list[Formula] = Field(default_factory=list, max_length=MAX_FORMULAS)
    objective: str = Field(max_length=MAX_NAME_LENGTH)
    constraints: list[str] = Field(default_factory=list, max_length=MAX_VARIABLES)

    @field_validator("objective")
    @classmethod
    def validate_objective(cls, v: str) -> str:
        if not _IDENTIFIER_RE.match(v):
            raise ValueError(f"Objective '{v}' is not a valid identifier")
        return v

    @model_validator(mode="after")
    def validate_model(self) -> "DecisionModel":
        # Check variable name uniqueness
        var_names = [v.name for v in self.variables]
        if len(var_names) != len(set(var_names)):
            raise ValueError("Variable names must be unique")

        # Check formula name uniqueness
        formula_names = [f.name for f in self.formulas]
        if len(formula_names) != len(set(formula_names)):
            raise ValueError("Formula names must be unique")

        # Check formula names don't clash with variable names
        all_names = set(var_names) | set(formula_names)
        if len(all_names) != len(var_names) + len(formula_names):
            raise ValueError("Formula names cannot duplicate variable names")

        # Check objective references an existing variable or formula
        if self.objective not in all_names:
            raise ValueError(
                f"Objective '{self.objective}' does not match any variable or formula name"
            )

        return self

    def get_all_names(self) -> set[str]:
        """Return the set of all variable and formula names."""
        return {v.name for v in self.variables} | {f.name for f in self.formulas}
