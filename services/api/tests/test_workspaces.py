"""Tests for workspace CRUD and cross-workspace isolation."""

from __future__ import annotations

from tests.conftest import register_and_login


def _get_workspace_id(client, headers):
    """Helper: get the first workspace ID for the logged-in user."""
    resp = client.get("/api/v1/workspaces", headers=headers)
    assert resp.status_code == 200
    return resp.json()[0]["id"]


class TestWorkspaceList:
    def test_list_workspaces_after_register(self, client):
        headers = register_and_login(client, email="wslist@test.com", name="WSList")
        resp = client.get("/api/v1/workspaces", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1
        ws = resp.json()[0]
        assert ws["name"] == "WSList's Workspace"
        assert ws["my_role"] == "owner"

    def test_list_workspaces_unauthenticated(self, client):
        resp = client.get("/api/v1/workspaces")
        assert resp.status_code == 401


class TestWorkspaceCreate:
    def test_create_workspace(self, client):
        headers = register_and_login(client, email="create@test.com")
        resp = client.post("/api/v1/workspaces", json={"name": "New Team"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "New Team"
        assert resp.json()["my_role"] == "owner"

    def test_create_duplicate_slug(self, client):
        headers = register_and_login(client, email="dups@test.com")
        resp = client.post("/api/v1/workspaces", json={"name": "Same", "slug": "same-slug"}, headers=headers)
        assert resp.status_code == 201
        resp2 = client.post("/api/v1/workspaces", json={"name": "Other", "slug": "same-slug"}, headers=headers)
        assert resp2.status_code == 409


class TestWorkspaceIsolation:
    """Critical: user A must not be able to access user B's workspace."""

    def test_cannot_get_other_users_workspace(self, client):
        headers_a = register_and_login(client, email="alice@test.com", name="Alice")
        headers_b = register_and_login(client, email="bob@test.com", name="Bob")
        ws_a = _get_workspace_id(client, headers_a)

        # Bob tries to access Alice's workspace
        resp = client.get(f"/api/v1/workspaces/{ws_a}", headers=headers_b)
        assert resp.status_code == 403

    def test_cannot_list_members_of_other_workspace(self, client):
        headers_a = register_and_login(client, email="alice2@test.com", name="Alice2")
        headers_b = register_and_login(client, email="bob2@test.com", name="Bob2")
        ws_a = _get_workspace_id(client, headers_a)

        resp = client.get(f"/api/v1/workspaces/{ws_a}/members", headers=headers_b)
        assert resp.status_code == 403

    def test_cannot_add_member_to_other_workspace(self, client):
        headers_a = register_and_login(client, email="alice3@test.com", name="Alice3")
        headers_b = register_and_login(client, email="bob3@test.com", name="Bob3")
        ws_a = _get_workspace_id(client, headers_a)

        # Bob tries to add himself to Alice's workspace
        bob_id = client.get("/api/v1/me", headers=headers_b).json()["id"]
        resp = client.post(
            f"/api/v1/workspaces/{ws_a}/members",
            json={"user_id": bob_id, "role": "member"},
            headers=headers_a,  # Only owner/admin can add members
        )
        assert resp.status_code == 201

        # Now Bob can access
        resp2 = client.get(f"/api/v1/workspaces/{ws_a}/members", headers=headers_b)
        assert resp2.status_code == 200

    def test_viewer_cannot_add_members(self, client):
        headers_a = register_and_login(client, email="owner@test.com", name="Owner")
        headers_b = register_and_login(client, email="viewer@test.com", name="Viewer")
        ws_a = _get_workspace_id(client, headers_a)

        bob_id = client.get("/api/v1/me", headers=headers_b).json()["id"]
        # Add Bob as viewer
        resp = client.post(
            f"/api/v1/workspaces/{ws_a}/members",
            json={"user_id": bob_id, "role": "viewer"},
            headers=headers_a,
        )
        assert resp.status_code == 201

        # Bob (viewer) tries to add someone
        headers_c = register_and_login(client, email="charlie@test.com", name="Charlie")
        charlie_id = client.get("/api/v1/me", headers=headers_c).json()["id"]
        resp2 = client.post(
            f"/api/v1/workspaces/{ws_a}/members",
            json={"user_id": charlie_id, "role": "member"},
            headers=headers_b,
        )
        assert resp2.status_code == 403

    def test_workspace_not_found(self, client):
        headers = register_and_login(client, email="nf@test.com")
        resp = client.get("/api/v1/workspaces/nonexistent-id", headers=headers)
        assert resp.status_code == 404


class TestMemberManagement:
    def test_update_member_role(self, client):
        headers_a = register_and_login(client, email="admin@test.com", name="Admin")
        headers_b = register_and_login(client, email="member@test.com", name="Member")
        ws_a = _get_workspace_id(client, headers_a)

        bob_id = client.get("/api/v1/me", headers=headers_b).json()["id"]
        client.post(
            f"/api/v1/workspaces/{ws_a}/members",
            json={"user_id": bob_id, "role": "member"},
            headers=headers_a,
        )

        # Promote Bob to admin
        resp = client.patch(
            f"/api/v1/workspaces/{ws_a}/members/{bob_id}",
            json={"role": "admin"},
            headers=headers_a,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

    def test_remove_member(self, client):
        headers_a = register_and_login(client, email="rem@test.com", name="Rem")
        headers_b = register_and_login(client, email="rem2@test.com", name="Rem2")
        ws_a = _get_workspace_id(client, headers_a)

        bob_id = client.get("/api/v1/me", headers=headers_b).json()["id"]
        client.post(
            f"/api/v1/workspaces/{ws_a}/members",
            json={"user_id": bob_id, "role": "member"},
            headers=headers_a,
        )

        resp = client.delete(f"/api/v1/workspaces/{ws_a}/members/{bob_id}", headers=headers_a)
        assert resp.status_code == 204

        # Bob can no longer access
        resp2 = client.get(f"/api/v1/workspaces/{ws_a}", headers=headers_b)
        assert resp2.status_code == 403

    def test_cannot_remove_owner(self, client):
        headers = register_and_login(client, email="ownrem@test.com", name="Owner")
        ws_id = _get_workspace_id(client, headers)
        user_id = client.get("/api/v1/me", headers=headers).json()["id"]

        resp = client.delete(f"/api/v1/workspaces/{ws_id}/members/{user_id}", headers=headers)
        assert resp.status_code == 400
