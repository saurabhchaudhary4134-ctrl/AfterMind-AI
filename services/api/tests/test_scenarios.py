"""Tests for scenario CRUD, duplication, and isolation."""

from __future__ import annotations

from tests.conftest import register_and_login


def _get_ws(client, headers):
    resp = client.get("/api/v1/workspaces", headers=headers)
    return resp.json()[0]["id"]


def _create_decision(client, headers, ws_id):
    resp = client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": "Test Decision", "description": "Test", "objective": "Max profit"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_scenario(client, headers, ws_id, decision_id, name="Base Scenario"):
    resp = client.post(
        f"/api/v1/scenarios?workspace_id={ws_id}",
        json={
            "decision_id": decision_id,
            "name": name,
            "description": "Base case",
            "assumption_overrides": {"revenue": {"params": {"mean": 1000}}},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestScenarioCRUD:
    def test_create_and_get(self, client):
        headers = register_and_login(client, email="sc@test.com", name="SC")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did, "My Scenario")

        resp = client.get(f"/api/v1/scenarios/{sid}?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["name"] == "My Scenario"

    def test_list_scenarios(self, client):
        headers = register_and_login(client, email="sc2@test.com", name="SC2")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id)
        _create_scenario(client, headers, ws_id, did, "A")
        _create_scenario(client, headers, ws_id, did, "B")

        resp = client.get(f"/api/v1/scenarios?decision_id={did}&workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_update_scenario(self, client):
        headers = register_and_login(client, email="sc3@test.com", name="SC3")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did, "Orig")

        resp = client.put(
            f"/api/v1/scenarios/{sid}?workspace_id={ws_id}",
            json={"name": "Updated", "description": "New desc"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated"

    def test_delete_scenario(self, client):
        headers = register_and_login(client, email="sc4@test.com", name="SC4")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did, "Delete")

        resp = client.delete(f"/api/v1/scenarios/{sid}?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 204

        resp2 = client.get(f"/api/v1/scenarios/{sid}?workspace_id={ws_id}", headers=headers)
        assert resp2.status_code == 404


class TestScenarioDuplicate:
    def test_duplicate_copies_overrides(self, client):
        headers = register_and_login(client, email="dup@test.com", name="Dup")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id)
        sid = _create_scenario(client, headers, ws_id, did, "Original")

        resp = client.post(f"/api/v1/scenarios/{sid}/duplicate?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Original (copy)"
        # Check overrides are copied
        assert resp.json()["assumption_overrides"] == {"revenue": {"params": {"mean": 1000}}}


class TestScenarioIsolation:
    def test_cannot_access_other_workspace_scenario(self, client):
        headers_a = register_and_login(client, email="iso1@test.com", name="A")
        headers_b = register_and_login(client, email="iso2@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did_a = _create_decision(client, headers_a, ws_a)
        sid_a = _create_scenario(client, headers_a, ws_a, did_a, "Alice's")

        # Bob tries to access with his workspace_id
        resp = client.get(f"/api/v1/scenarios/{sid_a}?workspace_id={ws_b}", headers=headers_b)
        assert resp.status_code == 404

    def test_cannot_list_other_workspace_scenarios(self, client):
        headers_a = register_and_login(client, email="iso3@test.com", name="A")
        headers_b = register_and_login(client, email="iso4@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did_a = _create_decision(client, headers_a, ws_a)
        _create_scenario(client, headers_a, ws_a, did_a, "Secret")

        resp = client.get(
            f"/api/v1/scenarios?decision_id={did_a}&workspace_id={ws_b}",
            headers=headers_b,
        )
        assert resp.status_code == 404  # Decision not found in Bob's workspace
