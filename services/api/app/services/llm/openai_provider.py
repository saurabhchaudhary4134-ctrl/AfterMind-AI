"""OpenAI LLM provider — structured extraction using the OpenAI API.

Uses a structured prompt that returns a JSON schema validated by Pydantic.
LLM output is NEVER trusted directly — it is validated and returned as a
draft awaiting user confirmation. The LLM never authorizes DB access or
executes code.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.config import settings
from app.services.llm.base import (
    ExtractionDraft,
    ExtractedFormula,
    ExtractedVariable,
    LLMProvider,
)

logger = logging.getLogger(__name__)

_EXTRACTION_SYSTEM_PROMPT = """
You are a decision modeling assistant. Your job is to extract structured decision model
components from natural language text.

You MUST return ONLY valid JSON matching this schema — no markdown, no preamble:
{
  "title": "string (max 200 chars)",
  "description": "string (max 500 chars)",
  "objective": "identifier (snake_case, no spaces)",
  "suggested_variables": [
    {
      "name": "identifier (snake_case)",
      "label": "Human-readable label",
      "unit": "unit string or empty",
      "distribution_type": "normal|uniform|triangular|lognormal|beta|constant",
      "distribution_params": {"mean": 0, "std": 1},
      "confidence": 0.0-1.0,
      "source_text": "verbatim phrase that suggested this"
    }
  ],
  "suggested_formulas": [
    {
      "name": "identifier",
      "expression": "arithmetic expression using only variable names and +,-,*,/,**,()",
      "description": "what this computes",
      "confidence": 0.0-1.0
    }
  ],
  "missing_assumptions": ["list of things not specified that are needed for simulation"]
}

Rules:
- Variable names must be valid Python identifiers (letters, digits, underscores, no leading digit).
- Formulas use ONLY: +, -, *, /, **, (, ), and variable names. No function calls.
- Distribution params must match the type: normal={mean,std}, uniform={low,high},
  triangular={low,peak,high}, lognormal={mean,sigma}, beta={alpha,beta}, constant={value}.
- Confidence is your estimate of how accurately you extracted this vs the source text.
- Flag EVERYTHING that is assumed rather than stated as a missing_assumption.
- If you cannot extract meaningful variables, return an empty list and explain in missing_assumptions.
""".strip()


class OpenAIProvider(LLMProvider):
    """OpenAI provider using the chat completions API."""

    def __init__(self) -> None:
        self._client = None

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(settings.LLM_API_KEY and settings.LLM_PROVIDER == "openai")

    def _get_client(self):
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=settings.LLM_API_KEY,
                    timeout=settings.LLM_TIMEOUT_SECONDS,
                )
            except ImportError:
                raise RuntimeError("openai package not installed. Install with: pip install openai")
        return self._client

    def extract_decision(self, text: str, max_tokens: int = 2000) -> ExtractionDraft:
        """Extract a structured draft using OpenAI chat completions.

        LLM output is validated with Pydantic. Invalid JSON triggers graceful
        fallback. The result requires user confirmation before use.
        """
        client = self._get_client()

        for attempt in range(settings.LLM_MAX_RETRIES + 1):
            try:
                response = client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=[
                        {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract decision model components from:\n\n{text[:3000]}"},
                    ],
                    max_tokens=min(max_tokens, settings.LLM_MAX_TOKENS),
                    temperature=0.1,  # Low temperature for deterministic extraction
                )
                raw = response.choices[0].message.content or ""
                return self._parse_response(raw)
            except Exception as exc:
                logger.warning(f"OpenAI extraction attempt {attempt + 1} failed: {exc}")
                if attempt == settings.LLM_MAX_RETRIES:
                    raise RuntimeError(f"LLM extraction failed after {settings.LLM_MAX_RETRIES + 1} attempts: {exc}") from exc

        raise RuntimeError("Unreachable")  # pragma: no cover

    def _parse_response(self, raw: str) -> ExtractionDraft:
        """Parse and validate the LLM JSON response."""
        # Strip markdown fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned invalid JSON: {exc}") from exc

        # Validate sub-objects with Pydantic — catch bad LLM output early
        variables = []
        for v in data.get("suggested_variables", []):
            try:
                variables.append(ExtractedVariable.model_validate(v))
            except Exception:
                pass  # Skip invalid variables silently

        formulas = []
        for f in data.get("suggested_formulas", []):
            try:
                formulas.append(ExtractedFormula.model_validate(f))
            except Exception:
                pass

        return ExtractionDraft(
            title=str(data.get("title", ""))[:200],
            description=str(data.get("description", ""))[:500],
            objective=str(data.get("objective", "")),
            suggested_variables=variables,
            suggested_formulas=formulas,
            missing_assumptions=[str(m) for m in data.get("missing_assumptions", [])],
            confidence=float(data.get("confidence", 0.5)),
            provider=self.name,
            model=settings.LLM_MODEL,
            requires_confirmation=True,
        )

    def generate_explanation(self, run_summary: dict[str, Any], objective: str) -> str:
        """Generate a grounded explanation based ONLY on computed statistics."""
        client = self._get_client()

        # Build a prompt that lists only real computed numbers
        stats_text = "\n".join(f"  {k}: {v}" for k, v in run_summary.items()
                               if isinstance(v, (int, float)) and k not in ("n",))

        prompt = (
            f"You are given the following computed simulation statistics for '{objective}':\n"
            f"{stats_text}\n\n"
            "Write a 2-3 sentence plain-language explanation of these results. "
            "Reference ONLY the numbers above. Do NOT add any information not present "
            "in the statistics. Do NOT claim statistical significance. "
            "Note that these are simulated estimates based on user-provided assumptions."
        )

        try:
            response = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=300,
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.warning(f"Explanation generation failed: {exc}")
            return (
                f"The simulation produced a mean of {run_summary.get('mean', 0):.2f} "
                f"with a P5–P95 range of {run_summary.get('p5', 0):.2f} to {run_summary.get('p95', 0):.2f}. "
                "These are model estimates based on your inputs."
            )
