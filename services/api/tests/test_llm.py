"""Tests for LLM extraction: mock provider, unavailable fallback, grounded explanations."""

from __future__ import annotations

import os

import pytest

from tests.conftest import register_and_login


def _get_ws(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]


def _create_decision(client, headers, ws_id):
    return client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": "Revenue Decision", "objective": "profit"},
        headers=headers,
    ).json()["id"]


class TestMockExtractionProvider:
    """Test the mock LLM provider — always available, deterministic."""

    def test_mock_extraction_returns_draft(self, client):
        """Mock provider extracts variables from business text."""
        os.environ["LLM_PROVIDER"] = "mock"
        h = register_and_login(client, email="llm1@test.com", name="L1")
        ws = _get_ws(client, h)
        did = _create_decision(client, h, ws)

        resp = client.post(
            f"/api/v1/decisions/{did}/extract?workspace_id={ws}",
            json={"text": "We expect revenue of around $100k and costs of $60k. Profit is the key metric."},
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["confirmed"] is False
        assert "confirmation_required_message" in data
        draft = data["draft"]
        assert draft["requires_confirmation"] is True
        assert len(draft["suggested_variables"]) > 0
        var_names = [v["name"] for v in draft["suggested_variables"]]
        assert "revenue" in var_names or "costs" in var_names

    def test_mock_extraction_flags_missing_assumptions(self, client):
        """Vague input should produce missing_assumptions."""
        os.environ["LLM_PROVIDER"] = "mock"
        h = register_and_login(client, email="llm2@test.com", name="L2")
        ws = _get_ws(client, h)
        did = _create_decision(client, h, ws)

        resp = client.post(
            f"/api/v1/decisions/{did}/extract?workspace_id={ws}",
            json={"text": "Should I open a new office?"},
            headers=h,
        )
        assert resp.status_code == 200
        draft = resp.json()["draft"]
        # Vague text → missing assumptions
        assert len(draft["missing_assumptions"]) > 0

    def test_extraction_requires_membership(self, client):
        """Non-member cannot trigger extraction."""
        os.environ["LLM_PROVIDER"] = "mock"
        h_a = register_and_login(client, email="llm3a@test.com", name="A")
        h_b = register_and_login(client, email="llm3b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision(client, h_a, ws_a)

        resp = client.post(
            f"/api/v1/decisions/{did}/extract?workspace_id={ws_b}",
            json={"text": "Should we expand?"},
            headers=h_b,
        )
        assert resp.status_code in (403, 404)


class TestLLMUnavailableFallback:
    """Without a configured LLM provider, extraction returns 503 and core sim still works."""

    def test_extraction_503_when_no_provider(self, client):
        """No LLM provider configured → 503."""
        os.environ["LLM_PROVIDER"] = ""
        h = register_and_login(client, email="llm4@test.com", name="L4")
        ws = _get_ws(client, h)
        did = _create_decision(client, h, ws)

        resp = client.post(
            f"/api/v1/decisions/{did}/extract?workspace_id={ws}",
            json={"text": "I want to expand my business."},
            headers=h,
        )
        assert resp.status_code == 503

    def test_simulation_works_without_llm(self, client):
        """Core simulation must work even when LLM is unavailable."""
        os.environ["LLM_PROVIDER"] = ""
        h = register_and_login(client, email="llm5@test.com", name="L5")
        ws = _get_ws(client, h)

        # Create decision with manually defined DNA
        did = client.post(
            f"/api/v1/decisions?workspace_id={ws}",
            json={"title": "Manual Decision", "objective": "profit"},
            headers=h,
        ).json()["id"]

        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws}",
            json={
                "decision_dna": {
                    "variables": [
                        {"name": "x", "label": "X", "unit": "", "distribution": {"type": "constant", "params": {"value": 42}}},
                    ],
                    "formulas": [],
                    "objective": "x",
                    "constraints": [],
                },
                "change_summary": "manual",
            },
            headers=h,
        )

        sc = client.post(
            f"/api/v1/scenarios?workspace_id={ws}",
            json={"decision_id": did, "name": "Base", "assumption_overrides": {}},
            headers=h,
        ).json()

        run = client.post(
            f"/api/v1/simulations?workspace_id={ws}",
            json={"decision_id": did, "scenario_id": sc["id"], "iterations": 100, "seed": 1},
            headers=h,
        ).json()
        assert run["status"] == "completed"


class TestGroundedExplanation:
    """Explanation endpoint must only reference real computed statistics."""

    def test_explanation_503_without_llm(self, client):
        """Explanation returns 503 when no LLM is configured."""
        os.environ["LLM_PROVIDER"] = ""
        h = register_and_login(client, email="llm6@test.com", name="L6")
        ws = _get_ws(client, h)

        # Create and run simulation
        did = client.post(
            f"/api/v1/decisions?workspace_id={ws}",
            json={"title": "D", "objective": "x"},
            headers=h,
        ).json()["id"]
        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws}",
            json={
                "decision_dna": {
                    "variables": [{"name": "x", "label": "X", "unit": "", "distribution": {"type": "constant", "params": {"value": 50}}}],
                    "formulas": [],
                    "objective": "x",
                    "constraints": [],
                },
                "change_summary": "init",
            },
            headers=h,
        )
        sc = client.post(
            f"/api/v1/scenarios?workspace_id={ws}",
            json={"decision_id": did, "name": "B", "assumption_overrides": {}},
            headers=h,
        ).json()
        run = client.post(
            f"/api/v1/simulations?workspace_id={ws}",
            json={"decision_id": did, "scenario_id": sc["id"], "iterations": 100, "seed": 1},
            headers=h,
        ).json()
        run_id = run["id"]

        resp = client.post(f"/api/v1/simulations/{run_id}/explain?workspace_id={ws}", headers=h)
        assert resp.status_code == 503

    def test_mock_explanation_references_real_stats(self, client):
        """Mock explanation must cite real statistics, not fabricated data."""
        os.environ["LLM_PROVIDER"] = "mock"
        h = register_and_login(client, email="llm7@test.com", name="L7")
        ws = _get_ws(client, h)

        did = client.post(
            f"/api/v1/decisions?workspace_id={ws}",
            json={"title": "D", "objective": "x"},
            headers=h,
        ).json()["id"]
        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws}",
            json={
                "decision_dna": {
                    "variables": [{"name": "x", "label": "X", "unit": "", "distribution": {"type": "constant", "params": {"value": 50}}}],
                    "formulas": [],
                    "objective": "x",
                    "constraints": [],
                },
                "change_summary": "init",
            },
            headers=h,
        )
        sc = client.post(
            f"/api/v1/scenarios?workspace_id={ws}",
            json={"decision_id": did, "name": "B", "assumption_overrides": {}},
            headers=h,
        ).json()
        run = client.post(
            f"/api/v1/simulations?workspace_id={ws}",
            json={"decision_id": did, "scenario_id": sc["id"], "iterations": 100, "seed": 1},
            headers=h,
        ).json()
        run_id = run["id"]

        resp = client.post(f"/api/v1/simulations/{run_id}/explain?workspace_id={ws}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert "explanation" in data
        assert "explanation_note" in data
        # Explanation must mention actual computed mean (50 for constant distribution)
        assert "50" in data["explanation"]
        assert data["explanation_note"] != ""
