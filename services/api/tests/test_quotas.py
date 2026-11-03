"""Tests for quota enforcement and usage tracking."""

from __future__ import annotations

from tests.conftest import register_and_login


def _get_ws(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]


def _create_sim(client, headers, ws_id):
    d = client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": "D", "objective": "x"},
        headers=headers,
    ).json()
    did = d["id"]
    client.put(
        f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
        json={
            "decision_dna": {
                "variables": [{"name": "x", "label": "X", "unit": "",
                               "distribution": {"type": "constant", "params": {"value": 1}}}],
                "formulas": [],
                "objective": "x",
                "constraints": [],
            },
            "change_summary": "init",
        },
        headers=headers,
    )
    sc = client.post(
        f"/api/v1/scenarios?workspace_id={ws_id}",
        json={"decision_id": did, "name": "B", "assumption_overrides": {}},
        headers=headers,
    ).json()
    return client.post(
        f"/api/v1/simulations?workspace_id={ws_id}",
        json={"decision_id": did, "scenario_id": sc["id"], "iterations": 10, "seed": 1},
        headers=headers,
    )


class TestUsageEndpoint:
    def test_get_usage(self, client):
        h = register_and_login(client, email="q1@test.com", name="Q1")
        ws = _get_ws(client, h)

        resp = client.get(f"/api/v1/workspaces/{ws}/usage", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "free"
        assert "simulations" in data
        assert data["simulations"]["limit"] == 100  # free tier
        assert "max_iterations" in data

    def test_usage_increments_after_simulation(self, client):
        h = register_and_login(client, email="q2@test.com", name="Q2")
        ws = _get_ws(client, h)

        before = client.get(f"/api/v1/workspaces/{ws}/usage", headers=h).json()
        initial = before["simulations"]["used"]

        _create_sim(client, h, ws)

        after = client.get(f"/api/v1/workspaces/{ws}/usage", headers=h).json()
        assert after["simulations"]["used"] == initial + 1

    def test_usage_not_accessible_by_non_member(self, client):
        h_a = register_and_login(client, email="q3a@test.com", name="A")
        h_b = register_and_login(client, email="q3b@test.com", name="B")
        ws_a = _get_ws(client, h_a)

        resp = client.get(f"/api/v1/workspaces/{ws_a}/usage", headers=h_b)
        assert resp.status_code == 403


class TestSubscriptionEndpoint:
    def test_get_subscription(self, client):
        h = register_and_login(client, email="sub1@test.com", name="S1")
        ws = _get_ws(client, h)

        resp = client.get(f"/api/v1/workspaces/{ws}/subscription", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] == "free"
        assert data["status"] == "active"
