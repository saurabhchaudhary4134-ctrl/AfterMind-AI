"""AfterMind AI — Simulation Engine.

A pure-Python, independently tested mathematical engine for decision modeling
and Monte Carlo simulation. This package has ZERO imports from FastAPI,
SQLAlchemy, Celery, or any HTTP/database code.
"""

from app.simulation.engine import SimulationEngine, run_simulation
from app.simulation.schema import (
    DecisionModel,
    Distribution,
    DistributionType,
    Formula,
    Variable,
)

ENGINE_VERSION = "1.0.0"

__all__ = [
    "ENGINE_VERSION",
    "SimulationEngine",
    "run_simulation",
    "DecisionModel",
    "Distribution",
    "DistributionType",
    "Formula",
    "Variable",
]
