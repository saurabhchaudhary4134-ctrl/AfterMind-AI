"""Tests for decision CRUD, version history, and IDOR prevention."""

from __future__ import annotations

from tests.conftest import register_and_login


def _get_ws(client, headers):
    resp = client.get("/api/v1/workspaces", headers=headers)
    return resp.json()[0]["id"]


def _create_decision(client, headers, ws_id, title="Test Decision"):
    resp = client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": title, "description": "A test", "objective": "Maximize profit"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


class TestDecisionCRUD:
    def test_create_and_get(self, client):
        headers = register_and_login(client, email="dec@test.com", name="Dec")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id, "New Decision")
        resp = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Decision"
        assert resp.json()["status"] == "draft"

    def test_list_decisions(self, client):
        headers = register_and_login(client, email="dec2@test.com", name="Dec2")
        ws_id = _get_ws(client, headers)
        _create_decision(client, headers, ws_id, "A")
        _create_decision(client, headers, ws_id, "B")
        resp = client.get(f"/api/v1/decisions?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_update_decision(self, client):
        headers = register_and_login(client, email="dec3@test.com", name="Dec3")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id, "Original")
        resp = client.put(
            f"/api/v1/decisions/{did}?workspace_id={ws_id}",
            json={"title": "Updated", "status": "active"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated"
        assert resp.json()["status"] == "active"

    def test_delete_decision(self, client):
        headers = register_and_login(client, email="dec4@test.com", name="Dec4")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id, "To Delete")
        resp = client.delete(f"/api/v1/decisions/{did}?workspace_id={ws_id}", headers=headers)
        assert resp.status_code == 204
        resp2 = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_id}", headers=headers)
        assert resp2.status_code == 404


class TestVersionHistory:
    def test_dna_update_creates_version(self, client):
        headers = register_and_login(client, email="ver@test.com", name="Ver")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id, "Versioned")

        # First DNA version
        resp = client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
            json={
                "decision_dna": {"variables": [{"name": "revenue"}], "formulas": []},
                "change_summary": "Initial DNA",
            },
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["version_number"] == 1

        # Second DNA version
        resp2 = client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
            json={
                "decision_dna": {"variables": [{"name": "revenue"}, {"name": "costs"}], "formulas": []},
                "change_summary": "Added costs variable",
            },
            headers=headers,
        )
        assert resp2.status_code == 200
        assert resp2.json()["version_number"] == 2

        # List all versions
        resp3 = client.get(f"/api/v1/decisions/{did}/versions?workspace_id={ws_id}", headers=headers)
        assert resp3.status_code == 200
        assert len(resp3.json()) == 2
        assert resp3.json()[0]["version_number"] == 1
        assert resp3.json()[1]["version_number"] == 2

    def test_get_specific_version(self, client):
        headers = register_and_login(client, email="ver2@test.com", name="Ver2")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id, "GetVer")
        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
            json={"decision_dna": {"v": 1}, "change_summary": "v1"},
            headers=headers,
        )
        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
            json={"decision_dna": {"v": 2}, "change_summary": "v2"},
            headers=headers,
        )
        resp = client.get(
            f"/api/v1/decisions/{did}/versions/1?workspace_id={ws_id}",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["decision_dna"] == {"v": 1}

    def test_dna_update_activates_decision(self, client):
        headers = register_and_login(client, email="ver3@test.com", name="Ver3")
        ws_id = _get_ws(client, headers)
        did = _create_decision(client, headers, ws_id, "Activate")
        assert client.get(f"/api/v1/decisions/{did}?workspace_id={ws_id}", headers=headers).json()["status"] == "draft"
        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws_id}",
            json={"decision_dna": {"x": 1}, "change_summary": "Init"},
            headers=headers,
        )
        status_after = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_id}", headers=headers).json()["status"]
        assert status_after == "active"


class TestIDOR:
    """IDOR (Insecure Direct Object Reference) prevention — user B must not access user A's decisions."""

    def test_cannot_get_other_workspace_decision(self, client):
        headers_a = register_and_login(client, email="idor1@test.com", name="A")
        headers_b = register_and_login(client, email="idor2@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did = _create_decision(client, headers_a, ws_a, "Alice's Decision")

        # Bob tries to access Alice's decision using his own workspace_id
        resp = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_b}", headers=headers_b)
        assert resp.status_code == 404  # Not found in Bob's workspace

        # Bob tries to access Alice's decision using Alice's workspace_id (not a member)
        resp2 = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_a}", headers=headers_b)
        assert resp2.status_code == 403  # Not a member of Alice's workspace

    def test_cannot_update_other_workspace_decision(self, client):
        headers_a = register_and_login(client, email="idor3@test.com", name="A")
        headers_b = register_and_login(client, email="idor4@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did = _create_decision(client, headers_a, ws_a, "Protected")
        resp = client.put(
            f"/api/v1/decisions/{did}?workspace_id={ws_b}",
            json={"title": "Hacked"},
            headers=headers_b,
        )
        assert resp.status_code == 404

    def test_cannot_delete_other_workspace_decision(self, client):
        headers_a = register_and_login(client, email="idor5@test.com", name="A")
        headers_b = register_and_login(client, email="idor6@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did = _create_decision(client, headers_a, ws_a, "Safe")
        resp = client.delete(f"/api/v1/decisions/{did}?workspace_id={ws_b}", headers=headers_b)
        assert resp.status_code == 404

        # Verify it still exists for Alice
        resp2 = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_a}", headers=headers_a)
        assert resp2.status_code == 200

    def test_cannot_view_other_workspace_versions(self, client):
        headers_a = register_and_login(client, email="idor7@test.com", name="A")
        headers_b = register_and_login(client, email="idor8@test.com", name="B")
        ws_a = _get_ws(client, headers_a)
        ws_b = _get_ws(client, headers_b)

        did = _create_decision(client, headers_a, ws_a, "VerProtected")
        client.put(
            f"/api/v1/decisions/{did}/dna?workspace_id={ws_a}",
            json={"decision_dna": {"secret": True}, "change_summary": "v1"},
            headers=headers_a,
        )

        resp = client.get(f"/api/v1/decisions/{did}/versions?workspace_id={ws_b}", headers=headers_b)
        assert resp.status_code == 200
        assert resp.json() == []  # No versions visible from Bob's workspace
