"""Tests for actual outcome recording, forecast evaluation, and report export."""

from __future__ import annotations

from tests.conftest import register_and_login


def _get_ws(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]


def _create_decision_with_dna(client, headers, ws_id):
    d = client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": "D", "objective": "profit"},
        headers=headers,
    ).json()
    did = d["id"]
    client.put(
        f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
        json={
            "decision_dna": {
                "variables": [
                    {"name": "revenue", "label": "R", "unit": "$",
                     "distribution": {"type": "normal", "params": {"mean": 1000, "std": 200}}},
                    {"name": "costs", "label": "C", "unit": "$",
                     "distribution": {"type": "normal", "params": {"mean": 600, "std": 100}}},
                ],
                "formulas": [{"name": "profit", "expression": "revenue - costs", "description": ""}],
                "objective": "profit",
                "constraints": [],
            },
            "change_summary": "init",
        },
        headers=headers,
    )
    return did


def _run_simulation(client, headers, ws_id, did):
    sc = client.post(
        f"/api/v1/scenarios?workspace_id={ws_id}",
        json={"decision_id": did, "name": "Base", "assumption_overrides": {}},
        headers=headers,
    ).json()
    run = client.post(
        f"/api/v1/simulations?workspace_id={ws_id}",
        json={"decision_id": did, "scenario_id": sc["id"], "iterations": 1000, "seed": 42},
        headers=headers,
    ).json()
    return run["id"]


class TestOutcomes:
    def test_record_and_list_outcome(self, client):
        h = register_and_login(client, email="out1@test.com", name="O1")
        ws = _get_ws(client, h)
        did = _create_decision_with_dna(client, h, ws)

        resp = client.post(
            f"/api/v1/decisions/{did}/outcomes?workspace_id={ws}",
            json={"metric_name": "profit", "actual_value": 380.0, "notes": "Q1 result"},
            headers=h,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["metric_name"] == "profit"
        assert data["actual_value"] == 380.0

        list_resp = client.get(f"/api/v1/decisions/{did}/outcomes?workspace_id={ws}", headers=h)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

    def test_cannot_record_outcome_other_workspace(self, client):
        h_a = register_and_login(client, email="out2a@test.com", name="A")
        h_b = register_and_login(client, email="out2b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision_with_dna(client, h_a, ws_a)

        resp = client.post(
            f"/api/v1/decisions/{did}/outcomes?workspace_id={ws_b}",
            json={"metric_name": "profit", "actual_value": 100.0},
            headers=h_b,
        )
        assert resp.status_code in (403, 404)


class TestForecastEval:
    def test_eval_no_outcomes(self, client):
        h = register_and_login(client, email="eval1@test.com", name="E1")
        ws = _get_ws(client, h)
        did = _create_decision_with_dna(client, h, ws)

        resp = client.get(f"/api/v1/decisions/{did}/forecast-eval?workspace_id={ws}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_outcomes"] == 0
        assert "No actual outcomes" in data["limitation_note"]

    def test_eval_with_outcome_and_simulation(self, client):
        h = register_and_login(client, email="eval2@test.com", name="E2")
        ws = _get_ws(client, h)
        did = _create_decision_with_dna(client, h, ws)
        _run_simulation(client, h, ws, did)

        client.post(
            f"/api/v1/decisions/{did}/outcomes?workspace_id={ws}",
            json={"metric_name": "profit", "actual_value": 385.0},
            headers=h,
        )

        resp = client.get(f"/api/v1/decisions/{did}/forecast-eval?workspace_id={ws}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["n_outcomes"] == 1
        assert len(data["metrics"]) == 1
        m = data["metrics"][0]
        assert m["metric_name"] == "profit"
        assert m["actual_value"] == 385.0
        # Simulation mean should be ~400, so error should exist
        assert m["absolute_error"] is not None
        assert m["note"] != ""


class TestReports:
    def test_get_report(self, client):
        h = register_and_login(client, email="rep1@test.com", name="R1")
        ws = _get_ws(client, h)
        did = _create_decision_with_dna(client, h, ws)
        run_id = _run_simulation(client, h, ws, did)

        resp = client.get(f"/api/v1/reports/{run_id}?workspace_id={ws}", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == run_id
        assert data["status"] == "completed"
        assert data["objective"] == "profit"
        assert "mean" in data["summary"]

    def test_export_json(self, client):
        h = register_and_login(client, email="rep2@test.com", name="R2")
        ws = _get_ws(client, h)
        did = _create_decision_with_dna(client, h, ws)
        run_id = _run_simulation(client, h, ws, did)

        resp = client.get(f"/api/v1/reports/{run_id}/export?workspace_id={ws}&format=json", headers=h)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert "summary" in data
        assert data["seed"] == 42

    def test_export_csv(self, client):
        h = register_and_login(client, email="rep3@test.com", name="R3")
        ws = _get_ws(client, h)
        did = _create_decision_with_dna(client, h, ws)
        run_id = _run_simulation(client, h, ws, did)

        resp = client.get(f"/api/v1/reports/{run_id}/export?workspace_id={ws}&format=csv", headers=h)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "mean" in resp.text

    def test_report_not_found(self, client):
        h = register_and_login(client, email="rep4@test.com", name="R4")
        ws = _get_ws(client, h)
        resp = client.get(f"/api/v1/reports/nonexistent?workspace_id={ws}", headers=h)
        assert resp.status_code == 404

    def test_cannot_access_other_workspace_report(self, client):
        h_a = register_and_login(client, email="rep5a@test.com", name="A")
        h_b = register_and_login(client, email="rep5b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision_with_dna(client, h_a, ws_a)
        run_id = _run_simulation(client, h_a, ws_a, did)

        resp = client.get(f"/api/v1/reports/{run_id}?workspace_id={ws_b}", headers=h_b)
        assert resp.status_code == 404
