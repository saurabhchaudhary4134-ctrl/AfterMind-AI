"""Tests for authentication: register, login, refresh, protected routes."""

from __future__ import annotations

from tests.conftest import register_and_login


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "StrongPass1!",
            "full_name": "New User",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_email(self, client):
        register_and_login(client, email="dup@test.com")
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@test.com",
            "password": "StrongPass1!",
            "full_name": "Another",
        })
        assert resp.status_code == 409

    def test_register_short_password(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "short@test.com",
            "password": "123",
            "full_name": "Short",
        })
        assert resp.status_code == 422

    def test_register_creates_workspace(self, client):
        """Registration should auto-provision a personal workspace."""
        headers = register_and_login(client, email="ws@test.com", name="Bob")
        resp = client.get("/api/v1/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "ws@test.com"


class TestLogin:
    def test_login_success(self, client):
        register_and_login(client, email="login@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "Test1234!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client):
        register_and_login(client, email="wrongpw@test.com")
        resp = client.post("/api/v1/auth/login", json={
            "email": "wrongpw@test.com",
            "password": "WrongPassword!",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "ghost@test.com",
            "password": "Whatever1!",
        })
        assert resp.status_code == 401


class TestRefresh:
    def test_refresh_success(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "refresh@test.com",
            "password": "Test1234!",
            "full_name": "Refresh User",
        })
        refresh_token = resp.json()["refresh_token"]

        resp2 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert resp2.status_code == 200
        assert "access_token" in resp2.json()

    def test_refresh_with_access_token_fails(self, client):
        """An access token should not be accepted as a refresh token."""
        headers = register_and_login(client, email="rtok@test.com")
        access = headers["Authorization"].replace("Bearer ", "")
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": access})
        assert resp.status_code == 401

    def test_refresh_with_invalid_token(self, client):
        resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-token"})
        assert resp.status_code == 401


class TestProtectedRoute:
    def test_get_me_success(self, client):
        headers = register_and_login(client, email="me@test.com", name="Me")
        resp = client.get("/api/v1/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "me@test.com"
        assert resp.json()["full_name"] == "Me"

    def test_get_me_no_token(self, client):
        resp = client.get("/api/v1/me")
        assert resp.status_code == 401

    def test_get_me_invalid_token(self, client):
        resp = client.get("/api/v1/me", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 401

    def test_update_me(self, client):
        headers = register_and_login(client, email="update@test.com", name="Original")
        resp = client.put("/api/v1/me", json={"full_name": "Updated Name"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"
