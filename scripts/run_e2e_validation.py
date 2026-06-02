"""
End-to-end validation script for KIRP Enterprise.

This script is intentionally light-weight and relies only on HTTP calls
against a running API instance (default: http://localhost:8000).

Usage:
    python scripts/run_e2e_validation.py

Configure via env:
    API_BASE_URL   (default: http://localhost:8000)
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List

import requests


API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")


@dataclass
class TestContext:
    email: str
    password: str
    name: str
    token: str | None = None
    tenant_id: str | None = None


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


def _auth_headers(token: str | None) -> Dict[str, str]:
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _post(path: str, json: dict[str, Any] | None = None, token: str | None = None) -> requests.Response:
    url = f"{API_BASE}{path}"
    resp = requests.post(url, json=json or {}, headers=_auth_headers(token), timeout=30)
    return resp


def _get(path: str, params: dict[str, Any] | None = None, token: str | None = None) -> requests.Response:
    url = f"{API_BASE}{path}"
    resp = requests.get(url, params=params or {}, headers=_auth_headers(token), timeout=30)
    return resp


def test_auth_flow(ctx: TestContext) -> None:
    _print_section("Auth: signup → login → me")

    # Signup
    r = _post(
        "/api/v1/auth/signup",
        {
            "email": ctx.email,
            "password": ctx.password,
            "name": ctx.name,
        },
    )
    if r.status_code not in (200, 201, 400):
        raise RuntimeError(f"Signup failed: {r.status_code} {r.text}")
    if r.status_code in (200, 201):
        data = r.json()
        ctx.token = data["access_token"]
        ctx.tenant_id = data["user"]["tenant_id"]
        print(f"Signup ok, tenant={ctx.tenant_id}")
    else:
        print("Signup email already exists, proceeding with login.")

    # Login
    r = _post(
        "/api/v1/auth/login",
        {"email": ctx.email, "password": ctx.password},
    )
    r.raise_for_status()
    data = r.json()
    ctx.token = data["access_token"]
    ctx.tenant_id = data["user"]["tenant_id"]
    print(f"Login ok, tenant={ctx.tenant_id}")

    # Me
    r = _get("/api/v1/auth/me", token=ctx.token)
    r.raise_for_status()
    me = r.json()
    assert me["email"].lower() == ctx.email.lower()
    print("Me ok")

    # Unauthorized access
    r = _get("/api/v1/history")
    assert r.status_code in (401, 403), f"Expected 401/403 for unauth history, got {r.status_code}"
    print("Unauthorized access correctly rejected")


def test_tasks_and_nodes(ctx: TestContext) -> None:
    _print_section("Tasks / Nodes")
    assert ctx.token and ctx.tenant_id

    # Create task
    r = _post(
        "/api/v1/tasks",
        {
            "title": "E2E Task",
            "description": "Created by run_e2e_validation",
            "status": "pending",
        },
        token=ctx.token,
        params=None,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Create task failed: {r.status_code} {r.text}")
    task = r.json()["data"]
    task_id = task["id"]
    print(f"Task created: {task_id}")

    # Update task
    r = requests.patch(
        f"{API_BASE}/api/v1/nodes/{task_id}",
        json={"title": "E2E Task Updated"},
        params={"tenant_id": ctx.tenant_id, "user_id": "e2e"},
        headers=_auth_headers(ctx.token),
        timeout=30,
    )
    r.raise_for_status()
    print("Task updated")

    # Complete task
    r = requests.patch(
        f"{API_BASE}/api/v1/nodes/{task_id}",
        json={"status": "completed"},
        params={"tenant_id": ctx.tenant_id, "user_id": "e2e"},
        headers=_auth_headers(ctx.token),
        timeout=30,
    )
    r.raise_for_status()
    print("Task completed")


def test_history_and_notifications(ctx: TestContext) -> None:
    _print_section("History & Notifications")
    assert ctx.token

    # History list
    r = _get("/api/v1/history", params={"limit": 20}, token=ctx.token)
    r.raise_for_status()
    entries = r.json()
    print(f"History entries: {len(entries)}")

    # Notifications unread count
    r = _get(
        "/api/v1/notifications/unread-count",
        params={"tenant_id": ctx.tenant_id, "user_id": "e2e"},
        token=ctx.token,
    )
    if r.status_code == 200:
        print("Notifications unread-count endpoint ok")


def main() -> None:
    email = os.getenv("E2E_EMAIL", "e2e-user@example.com")
    password = os.getenv("E2E_PASSWORD", "e2e-password-123")
    name = os.getenv("E2E_NAME", "E2E User")

    ctx = TestContext(email=email, password=password, name=name)

    try:
        test_auth_flow(ctx)
        test_tasks_and_nodes(ctx)
        test_history_and_notifications(ctx)
        print("\nE2E validation (subset) completed without fatal errors.")
    except Exception as e:
        print(f"\nE2E validation FAILED: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

