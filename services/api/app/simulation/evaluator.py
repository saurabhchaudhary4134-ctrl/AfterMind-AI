"""Safe formula evaluator — restricted expression parser with dependency resolution.

Uses `simpleeval` (a safe-eval library) with a locked-down evaluator that:
  - Allows only +, -, *, /, **, %, unary minus, and parentheses.
  - Resolves names from a provided namespace (variable values).
  - Rejects function calls, attribute access, imports, and builtins.
  - Performs topological sorting for multi-formula dependency resolution.
  - Detects circular dependencies before evaluation.

NO imports from FastAPI, SQLAlchemy, Celery, or HTTP/DB code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from simpleeval import EvalWithCompoundTypes, NameNotDefined, SimpleEval


class FormulaError(Exception):
    """Raised when a formula is invalid or cannot be evaluated safely."""


class CircularDependencyError(FormulaError):
    """Raised when a circular dependency is detected among formulas/variables."""


# Pattern to extract identifier references from an expression
# Matches word characters that aren't numbers (e.g. revenue, costs, profit)
_IDENTIFIER_REF_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")

# Hard-blocked names that should never appear in expressions
_BLOCKED_NAMES = frozenset({
    "__import__", "eval", "exec", "compile", "open", "input", "globals",
    "locals", "vars", "dir", "getattr", "setattr", "delattr", "hasattr",
    "type", "object", "classmethod", "staticmethod", "property",
    "__builtins__", "__class__", "__bases__", "__subclasses__", "__dict__",
    "exit", "quit", "help", "license", "copyright", "credits",
    "os", "sys", "subprocess", "shutil", "pathlib", "pickle", "marshal",
    "ctypes", "multiprocessing", "threading", "socket", "http",
    "urllib", "requests", "builtins",
})

# Allowed operators in the expression string (whitespace is fine too)
_ALLOWED_CHAR_RE = re.compile(r"^[a-zA-Z0-9_\s+\-*/%().,]+$")


class SafeEvaluator:
    """A restricted expression evaluator.

    Evaluates arithmetic expressions against a namespace of named values.
    No function calls, no attribute access, no builtins — only arithmetic
    and variable references.
    """

    def __init__(self) -> None:
        # Create a SimpleEval with no functions and no operators beyond defaults
        self._evaluator = SimpleEval(names={})
        # Lock down: no functions, no built-in names
        self._evaluator.functions = {}
        self._evaluator.names = {}

    def evaluate(self, expression: str, names: dict[str, float]) -> float:
        """Evaluate an arithmetic expression with the given variable bindings.

        Args:
            expression: e.g. "revenue * margin - costs"
            names: dict of variable/formula name → numeric value

        Returns:
            The computed float result.

        Raises:
            FormulaError: if the expression is invalid or unsafe.
        """
        self._validate_expression(expression, names)

        self._evaluator.names = names
        try:
            result = self._evaluator.eval(expression)
        except NameNotDefined as exc:
            raise FormulaError(f"Undefined variable in expression '{expression}': {exc}") from exc
        except ZeroDivisionError:
            raise FormulaError(f"Division by zero in expression '{expression}'") from None
        except SyntaxError as exc:
            raise FormulaError(f"Syntax error in expression '{expression}': {exc}") from exc
        except Exception as exc:
            raise FormulaError(f"Error evaluating '{expression}': {exc}") from exc
        finally:
            self._evaluator.names = {}

        if not isinstance(result, (int, float)):
            raise FormulaError(
                f"Expression '{expression}' produced non-numeric result: {type(result).__name__}"
            )
        # Convert to float for consistency
        try:
            result = float(result)
        except (TypeError, ValueError) as exc:
            raise FormulaError(
                f"Expression '{expression}' result is not convertible to float: {exc}"
            ) from exc

        if isinstance(result, float):
            # Catch inf/nan
            if result != result:  # NaN check
                raise FormulaError(f"Expression '{expression}' produced NaN")
            if result == float("inf") or result == float("-inf"):
                raise FormulaError(f"Expression '{expression}' produced infinity")

        return result

    @staticmethod
    def _validate_expression(expression: str, allowed_names: dict[str, float]) -> None:
        """Validate that the expression is safe and only references allowed names."""
        if not expression or not expression.strip():
            raise FormulaError("Expression is empty")

        if len(expression) > 1000:
            raise FormulaError("Expression exceeds maximum length of 1000 characters")

        # Check for forbidden characters
        if not _ALLOWED_CHAR_RE.match(expression):
            raise FormulaError(
                f"Expression contains disallowed characters: '{expression}'"
            )

        # Extract all identifiers referenced in the expression
        referenced = set(_IDENTIFIER_REF_RE.findall(expression))

        # Check for blocked names
        blocked_found = referenced & _BLOCKED_NAMES
        if blocked_found:
            raise FormulaError(
                f"Expression contains blocked identifiers: {sorted(blocked_found)}"
            )

        # Check that all referenced names are in the allowed namespace
        unknown = referenced - set(allowed_names.keys())
        if unknown:
            raise FormulaError(
                f"Expression references undefined variables: {sorted(unknown)}"
            )


@dataclass
class _DependencyNode:
    """Node in the dependency graph for topological sorting."""
    name: str
    depends_on: set[str] = field(default_factory=set)


def extract_references(expression: str) -> set[str]:
    """Extract all identifier references from an arithmetic expression.

    This is used for dependency analysis, not evaluation.
    """
    if not _ALLOWED_CHAR_RE.match(expression):
        raise FormulaError(f"Expression contains disallowed characters: '{expression}'")
    refs = set(_IDENTIFIER_REF_RE.findall(expression))
    # Filter out blocked names
    refs -= _BLOCKED_NAMES
    return refs


def topological_sort(
    variables: list[str],
    formulas: dict[str, str],
) -> list[str]:
    """Topologically sort variables and formulas by dependency.

    Variables have no dependencies (they're sampled directly).
    Formulas depend on other variables/formulas referenced in their expressions.

    Args:
        variables: list of variable names (no dependencies)
        formulas: dict of formula_name → expression_string

    Returns:
        List of names in evaluation order (dependencies first).

    Raises:
        CircularDependencyError: if a cycle is detected.
        FormulaError: if a formula references an undefined name.
    """
    all_var_names = set(variables)
    all_formula_names = set(formulas.keys())
    all_names = all_var_names | all_formula_names

    # Build dependency graph
    nodes: dict[str, _DependencyNode] = {}
    for name in all_var_names:
        nodes[name] = _DependencyNode(name=name, depends_on=set())
    for name, expr in formulas.items():
        refs = extract_references(expr)
        # All references must be known names
        unknown = refs - all_names
        if unknown:
            raise FormulaError(
                f"Formula '{name}' references undefined names: {sorted(unknown)}"
            )
        nodes[name] = _DependencyNode(name=name, depends_on=refs)

    # Kahn's algorithm for topological sort
    # Start with nodes that have no dependencies
    order: list[str] = []
    remaining = dict(nodes)

    while remaining:
        # Find all nodes whose dependencies are all already resolved
        ready = [
            name for name, node in remaining.items()
            if node.depends_on <= set(order)
        ]
        if not ready:
            # Remaining nodes all have unresolvable dependencies → cycle
            cycle_nodes = sorted(remaining.keys())
            unresolved = {
                n: sorted(node.depends_on - set(order))
                for n, node in remaining.items()
            }
            raise CircularDependencyError(
                f"Circular dependency detected among: {cycle_nodes}. "
                f"Unresolved: {unresolved}"
            )
        # Sort for deterministic ordering
        ready.sort()
        for name in ready:
            order.append(name)
            del remaining[name]

    return order


def evaluate_model(
    variable_values: dict[str, float],
    formulas: dict[str, str],
) -> dict[str, float]:
    """Evaluate all formulas in dependency order.

    Args:
        variable_values: pre-sampled variable values (name → float)
        formulas: dict of formula_name → expression_string

    Returns:
        dict of all names (variables + formulas) → float values.

    Raises:
        FormulaError, CircularDependencyError
    """
    evaluator = SafeEvaluator()
    order = topological_sort(list(variable_values.keys()), formulas)

    namespace = dict(variable_values)
    for name in order:
        if name in formulas:
            namespace[name] = evaluator.evaluate(formulas[name], namespace)

    return namespace
