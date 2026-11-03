"""Tests for simulation runs: create, execute (sync), results, immutability, cancel."""

from __future__ import annotations

import pytest

from tests.conftest import register_and_login


def _get_ws(client, headers):
    resp = client.get("/api/v1/workspaces", headers=headers)
    return resp.json()[0]["id"]


def _create_decision_with_dna(client, headers, ws_id):
    """Create a decision and set up its Decision DNA."""
    resp = client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": "Pricing Decision", "description": "Price optimization", "objective": "profit"},
        headers=headers,
    )
    did = resp.json()["id"]

    # Set DNA with variables and formulas
    dna_resp = client.put(
        f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
        json={
            "decision_dna": {
                "variables": [
                    {
                        "name": "revenue",
                        "label": "Revenue",
                        "unit": "$",
                        "distribution": {"type": "normal", "params": {"mean": 1000, "std": 200}},
                    },
                    {
                        "name": "costs",
                        "label": "Costs",
                        "unit": "$",
                        "distribution": {"type": "normal", "params": {"mean": 600, "std": 100}},
                    },
                ],
                "formulas": [
                    {
                        "name": "profit",
                        "expression": "revenue - costs",
                        "description": "Profit = Revenue - Costs",
                    },
                ],
                "objective": "profit",
                "constraints": [],
            },
            "change_summary": "Initial DNA",
        },
        headers=headers,
    )
    assert dna_resp.status_code == 200, dna_resp.text
    return did


def _create_scenario(client, headers, ws_id, decision_id, name="Base Case"):
    resp = client.post(
        f"/api/v1/scenarios?workspace_id={ws_id}",
        json={
            "decision_id": decision_id,
            "name": name,
            "description": "Base scenario",
            "assumption_overrides": {},
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


class TestSimulationCreate:
    def test_create_run_sync_completes(self, client):
        """A simulation run created in sync mode should complete immediately."""
        headers = register_and_login(client, email="sim1@test.com", name="Sim")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={
                "decision_id": did,
                "scenario_id": sid,
                "iterations": 1000,
                "seed": 42,
            },
            headers=headers,
        )
        assert resp.status_code == 202, resp.text
        data = resp.json()
        assert data["status"] == "completed"
        assert data["iterations"] == 1000
        assert data["seed"] == 42
        assert data["progress"] == 100
        assert data["id"] is not None

    def test_create_run_no_dna_fails(self, client):
        """Creating a simulation for a decision without DNA should fail."""
        headers = register_and_login(client, email="sim2@test.com", name="Sim2")
        ws_id = _get_ws(client, headers)
        # Create decision but don't set DNA
        resp = client.post(
            f"/api/v1/decisions?workspace_id={ws_id}",
            json={"title": "No DNA", "objective": "x"},
            headers=headers,
        )
        did = resp.json()["id"]
        sid = _create_scenario(client, headers, ws_id, did)

        resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 100},
            headers=headers,
        )
        assert resp.status_code == 409

    def test_create_run_invalid_iterations(self, client):
        headers = register_and_login(client, email="sim3@test.com", name="Sim3")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 0},
            headers=headers,
        )
        assert resp.status_code == 422


class TestSimulationResults:
    def test_get_results(self, client):
        headers = register_and_login(client, email="res1@test.com", name="Res")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        run_resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 5000, "seed": 42},
            headers=headers,
        )
        run_id = run_resp.json()["id"]

        resp = client.get(f"/api/v1/simulations/{run_id}/results?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert data["status"] == "completed"
        assert data["objective"] == "profit"
        assert "mean" in data["summary"]
        assert "p50" in data["summary"]
        assert "cvar_5" in data["summary"]
        assert "bin_edges" in data["distribution_buckets"]
        assert "variables" in data["sensitivity"]

    def test_results_contain_real_statistics(self, client):
        """Results should contain real computed statistics, not fake values."""
        headers = register_and_login(client, email="res2@test.com", name="Res2")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        run_resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 10000, "seed": 42},
            headers=headers,
        )
        run_id = run_resp.json()["id"]

        resp = client.get(f"/api/v1/simulations/{run_id}/results?workspace_id={ws_id}", headers=headers)
        summary = resp.json()["summary"]

        # Revenue ~ N(1000, 200), Costs ~ N(600, 100), Profit = Revenue - Costs
        # E[Profit] = 1000 - 600 = 400
        # Var[Profit] = 200^2 + 100^2 = 50000, Std = ~224
        assert abs(summary["mean"] - 400) < 30  # Within reasonable sampling error
        assert abs(summary["std"] - 224) < 30
        assert summary["n"] == 10000

    def test_reproducible_results(self, client):
        """Same seed should produce same results."""
        headers = register_and_login(client, email="res3@test.com", name="Res3")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        run1 = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 1000, "seed": 42},
            headers=headers,
        )
        run2 = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 1000, "seed": 42},
            headers=headers,
        )

        r1 = client.get(f"/api/v1/simulations/{run1.json()['id']}/results?workspace_id={ws_id}", headers=headers)
        r2 = client.get(f"/api/v1/simulations/{run2.json()['id']}/results?workspace_id={ws_id}", headers=headers)

        assert r1.json()["summary"]["mean"] == r2.json()["summary"]["mean"]
        assert r1.json()["summary"]["p50"] == r2.json()["summary"]["p50"]


class TestSimulationStatus:
    def test_get_run_status(self, client):
        headers = register_and_login(client, email="stat@test.com", name="Stat")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        run_resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 100, "seed": 1},
            headers=headers,
        )
        run_id = run_resp.json()["id"]

        resp = client.get(f"/api/v1/simulations/{run_id}?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_list_simulations(self, client):
        headers = register_and_login(client, email="list@test.com", name="List")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        for i in range(3):
            client.post(
                f"/api/v1/simulations?workspace_id={ws_id}",
                json={"decision_id": did, "scenario_id": sid, "iterations": 100, "seed": i},
                headers=headers,
            )

        resp = client.get(f"/api/v1/simulations?decision_id={did}&workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 3


class TestSimulationImmutability:
    def test_completed_results_not_overwritten(self, client):
        """Re-running should create a new run, not overwrite existing results."""
        headers = register_and_login(client, email="imm@test.com", name="Imm")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        run1 = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 100, "seed": 42},
            headers=headers,
        )
        run2 = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 100, "seed": 42},
            headers=headers,
        )

        # Two different run IDs
        assert run1.json()["id"] != run2.json()["id"]

        # Both have their own results
        r1 = client.get(f"/api/v1/simulations/{run1.json()['id']}/results?workspace_id={ws_id}", headers=headers)
        r2 = client.get(f"/api/v1/simulations/{run2.json()['id']}/results?workspace_id={ws_id}", headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200


class TestSimulationCancel:
    def test_cancel_completed_run_fails(self, client):
        """Cannot cancel a run that already completed."""
        headers = register_and_login(client, email="can@test.com", name="Can")
        ws_id = _get_ws(client, headers)
        did = _create_decision_with_dna(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did)

        run_resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_id}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 100, "seed": 1},
            headers=headers,
        )
        run_id = run_resp.json()["id"]

        resp = client.post(f"/api/v1/simulations/{run_id}/cancel?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 409


class TestSimulationIsolation:
    def test_cannot_access_other_workspace_run(self, client):
        headers_a = register_and_login(client, email="siso1@test.com", name="A")
        headers_b = register_and_login(client, email="siso2@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did = _create_decision_with_dna(client, headers_a, ws_a)
        sid = _create_scenario(client, headers_a, ws_a, did)
        run_resp = client.post(
            f"/api/v1/simulations?workspace_id={ws_a}",
            json={"decision_id": did, "scenario_id": sid, "iterations": 100, "seed": 1},
            headers=headers_a,
        )
        run_id = run_resp.json()["id"]

        # Bob tries to access Alice's simulation
        resp = client.get(f"/api/v1/simulations/{run_id}?workspace_id={ws_b}", headers=headers_b)
        assert resp.status_code == 404

        resp2 = client.get(f"/api/v1/simulations/{run_id}/results?workspace_id={ws_b}", headers=headers_b)
        assert resp2.status_code == 404
