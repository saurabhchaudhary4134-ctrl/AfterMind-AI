"""Security tests: IDOR, injection prevention, oversized payloads,
cross-tenant reads, auth boundary, and rate limiting."""

from __future__ import annotations

import json
import time

import pytest

from tests.conftest import register_and_login


# ── Helpers ────────────────────────────────────────────────────

def _get_ws(client, headers):
    return client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]


def _create_decision(client, headers, ws_id, title="D"):
    r = client.post(
        f"/api/v1/decisions?workspace_id={ws_id}",
        json={"title": title, "objective": "x"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _set_dna(client, headers, ws_id, did):
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


# ── 1. Authentication boundary ─────────────────────────────────

class TestAuthBoundary:
    def test_unauthenticated_requests_rejected(self, client):
        """All protected endpoints return 401 without a token."""
        for path in ["/api/v1/me", "/api/v1/workspaces", "/api/v1/decisions?workspace_id=x"]:
            resp = client.get(path)
            assert resp.status_code == 401, f"Expected 401 for {path}, got {resp.status_code}"

    def test_tampered_token_rejected(self, client):
        headers = register_and_login(client, email="tamper@test.com")
        token = headers["Authorization"].replace("Bearer ", "")
        # Tamper the payload section of the JWT
        parts = token.split(".")
        tampered = parts[0] + ".XXXXXXXXXXXXXXXXXXXXX==" + parts[2]
        resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {tampered}"})
        assert resp.status_code == 401

    def test_refresh_token_cannot_be_used_as_access_token(self, client):
        reg = client.post("/api/v1/auth/register", json={
            "email": "rtaccess@test.com", "password": "Pass1234!", "full_name": "T"
        })
        refresh_token = reg.json()["refresh_token"]
        resp = client.get("/api/v1/me", headers={"Authorization": f"Bearer {refresh_token}"})
        assert resp.status_code == 401


# ── 2. IDOR prevention ─────────────────────────────────────────

class TestIDOR:
    def test_cannot_read_foreign_decision(self, client):
        h_a = register_and_login(client, email="idor_a@test.com", name="A")
        h_b = register_and_login(client, email="idor_b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision(client, h_a, ws_a)

        # Bob queries with his own workspace_id — gets 404 (not 403, which would reveal existence)
        resp = client.get(f"/api/v1/decisions/{did}?workspace_id={ws_b}", headers=h_b)
        assert resp.status_code == 404

    def test_cannot_delete_foreign_decision(self, client):
        h_a = register_and_login(client, email="idor_del_a@test.com", name="A")
        h_b = register_and_login(client, email="idor_del_b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision(client, h_a, ws_a)

        resp = client.delete(f"/api/v1/decisions/{did}?workspace_id={ws_b}", headers=h_b)
        assert resp.status_code == 404

        # Verify original still exists
        assert client.get(f"/api/v1/decisions/{did}?workspace_id={ws_a}", headers=h_a).status_code == 200

    def test_cannot_read_foreign_simulation(self, client):
        h_a = register_and_login(client, email="idor_sim_a@test.com", name="A")
        h_b = register_and_login(client, email="idor_sim_b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision(client, h_a, ws_a)
        _set_dna(client, h_a, ws_a, did)

        sc = client.post(
            f"/api/v1/scenarios?workspace_id={ws_a}",
            json={"decision_id": did, "name": "B", "assumption_overrides": {}},
            headers=h_a,
        ).json()
        run = client.post(
            f"/api/v1/simulations?workspace_id={ws_a}",
            json={"decision_id": did, "scenario_id": sc["id"], "iterations": 10, "seed": 1},
            headers=h_a,
        ).json()

        resp = client.get(f"/api/v1/simulations/{run['id']}?workspace_id={ws_b}", headers=h_b)
        assert resp.status_code == 404

    def test_cannot_read_foreign_report(self, client):
        h_a = register_and_login(client, email="idor_rep_a@test.com", name="A")
        h_b = register_and_login(client, email="idor_rep_b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        did = _create_decision(client, h_a, ws_a)
        _set_dna(client, h_a, ws_a, did)
        sc = client.post(
            f"/api/v1/scenarios?workspace_id={ws_a}",
            json={"decision_id": did, "name": "B", "assumption_overrides": {}},
            headers=h_a,
        ).json()
        run = client.post(
            f"/api/v1/simulations?workspace_id={ws_a}",
            json={"decision_id": did, "scenario_id": sc["id"], "iterations": 10, "seed": 1},
            headers=h_a,
        ).json()

        resp = client.get(f"/api/v1/reports/{run['id']}?workspace_id={ws_b}", headers=h_b)
        assert resp.status_code == 404


# ── 3. Cross-tenant isolation ──────────────────────────────────

class TestCrossTenant:
    def test_decisions_list_scoped_to_workspace(self, client):
        h_a = register_and_login(client, email="ct_a@test.com", name="A")
        h_b = register_and_login(client, email="ct_b@test.com", name="B")
        ws_a = _get_ws(client, h_a)
        ws_b = _get_ws(client, h_b)
        _create_decision(client, h_a, ws_a, "Alice Secret")
        _create_decision(client, h_a, ws_a, "Alice Secret 2")

        # Bob's list should be empty
        resp = client.get(f"/api/v1/decisions?workspace_id={ws_b}", headers=h_b)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_workspace_member_list_scoped(self, client):
        h_a = register_and_login(client, email="ct_mem_a@test.com", name="A")
        h_b = register_and_login(client, email="ct_mem_b@test.com", name="B")
        ws_a = _get_ws(client, h_a)

        resp = client.get(f"/api/v1/workspaces/{ws_a}/members", headers=h_b)
        assert resp.status_code == 403


# ── 4. Input validation & injection prevention ─────────────────

class TestInjectionPrevention:
    def test_formula_injection_rejected(self, client):
        """Malicious formula expressions must be rejected by the evaluator."""
        h = register_and_login(client, email="inj1@test.com", name="I")
        ws = _get_ws(client, h)
        did = _create_decision(client, h, ws)

        malicious_formulas = [
            "__import__('os').system('rm -rf /')",
            "eval('1+1')",
            "exec('import os')",
            "__builtins__['print']('pwned')",
        ]

        for expr in malicious_formulas:
            resp = client.put(
                f"/api/v1/decisions/{did}/dna?workspace_id={ws}",
                json={
                    "decision_dna": {
                        "variables": [{"name": "x", "label": "X", "unit": "",
                                       "distribution": {"type": "constant", "params": {"value": 1}}}],
                        "formulas": [{"name": "f", "expression": expr, "description": ""}],
                        "objective": "f",
                        "constraints": [],
                    },
                    "change_summary": "injection attempt",
                },
                headers=h,
            )
            # Either the simulation engine rejects it (422/400) or the formula validator catches it
            # during simulation — either way it must not succeed silently
            # The DNA can be stored (schema allows arbitrary expressions),
            # but the simulation must fail when run
            if resp.status_code == 201:
                # Create a scenario and try to run — must fail
                sc = client.post(
                    f"/api/v1/scenarios?workspace_id={ws}",
                    json={"decision_id": did, "name": "inj", "assumption_overrides": {}},
                    headers=h,
                ).json()
                run_resp = client.post(
                    f"/api/v1/simulations?workspace_id={ws}",
                    json={"decision_id": did, "scenario_id": sc["id"], "iterations": 1, "seed": 1},
                    headers=h,
                )
                # Run should fail (formula evaluation rejected malicious expression)
                if run_resp.status_code in (200, 202):
                    run_data = run_resp.json()
                    assert run_data.get("status") == "failed", \
                        f"Malicious formula '{expr}' did not fail — status: {run_data.get('status')}"

    def test_oversized_json_body_rejected(self, client):
        """Bodies exceeding MAX_BODY_SIZE_BYTES must be rejected with 413."""
        headers = register_and_login(client, email="size@test.com", name="S")
        ws = _get_ws(client, headers)

        # Craft a body that's clearly > 1MB by sending a content-length header
        # The middleware checks the Content-Length header, not the actual body
        big_title = "x" * 200
        resp = client.post(
            f"/api/v1/decisions?workspace_id={ws}",
            content='{"title":"x"}',
            headers={
                **headers,
                "Content-Type": "application/json",
                "Content-Length": "2000000",  # Signal 2MB body
            },
        )
        assert resp.status_code == 413

    def test_pydantic_rejects_invalid_schema(self, client):
        """Pydantic validation must reject badly shaped input with 422."""
        headers = register_and_login(client, email="pyd@test.com", name="P")
        ws = _get_ws(client, headers)

        resp = client.post(
            f"/api/v1/decisions?workspace_id={ws}",
            json={"title": "", "objective": "x"},  # empty title violates min_length=1
            headers=headers,
        )
        assert resp.status_code == 422


# ── 5. Rate limiting ───────────────────────────────────────────

class TestRateLimiting:
    def test_login_rate_limited_after_10_attempts(self, client):
        """More than 10 login attempts per IP per minute returns 429."""
        # Exhaust the 10-per-minute limit
        for _ in range(10):
            client.post("/api/v1/auth/login", json={
                "email": "nonexistent@test.com",
                "password": "WrongPass123!",
            })
        # 11th attempt should be rate-limited
        resp = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "WrongPass123!",
        })
        assert resp.status_code == 429

    def test_register_rate_limited(self, client):
        """More than 10 register attempts per IP per minute returns 429."""
        for i in range(10):
            client.post("/api/v1/auth/register", json={
                "email": f"ratelimit_r{i}@test.com",
                "password": "Test1234!",
                "full_name": "RL",
            })
        resp = client.post("/api/v1/auth/register", json={
            "email": "ratelimit_r_extra@test.com",
            "password": "Test1234!",
            "full_name": "RL",
        })
        assert resp.status_code == 429


# ── 6. No stack-traces in production-style errors ─────────────

class TestErrorSafety:
    def test_404_does_not_leak_internals(self, client):
        headers = register_and_login(client, email="safe@test.com", name="S")
        ws = _get_ws(client, headers)
        resp = client.get(f"/api/v1/decisions/does-not-exist?workspace_id={ws}", headers=headers)
        body = resp.text
        assert "Traceback" not in body
        assert "sqlalchemy" not in body.lower()

    def test_health_endpoint_available_without_auth(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
