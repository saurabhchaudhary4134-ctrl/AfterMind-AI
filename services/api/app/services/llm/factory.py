"""LLM provider factory — returns the configured provider or raises if unavailable."""

from __future__ import annotations

import os

from app.services.llm.base import LLMProvider


def _get_provider_name() -> str:
    """Read LLM_PROVIDER directly from environment (not cached settings)."""
    return (os.environ.get("LLM_PROVIDER") or "").lower()


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider.

    Reads LLM_PROVIDER from env at call time (not from cached config singleton)
    so tests can override it via os.environ.

    Raises RuntimeError if no provider is configured (caller should return 503).
    """
    provider_name = _get_provider_name()

    if provider_name == "openai":
        from app.services.llm.openai_provider import OpenAIProvider
        p = OpenAIProvider()
        if not p.is_available():
            raise RuntimeError("OpenAI provider configured but LLM_API_KEY is missing")
        return p

    if provider_name == "mock":
        from app.services.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()

    raise RuntimeError(
        f"No LLM provider configured (LLM_PROVIDER='{os.environ.get('LLM_PROVIDER', '')}')."
        " Set LLM_PROVIDER=openai and LLM_API_KEY, or LLM_PROVIDER=mock for testing."
    )


def get_mock_provider() -> LLMProvider:
    """Always return the mock provider — for tests."""
    from app.services.llm.mock_provider import MockLLMProvider
    return MockLLMProvider()
