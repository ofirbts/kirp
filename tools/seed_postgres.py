"""
Seed Postgres-backed projections and core identities via the public API.

This script:
- Calls /api/admin/bootstrap to create tenants, spaces, users, and roles
  based on seed/seed_definition.json.

Notes:
- This script is intentionally API-driven to preserve event-sourcing and
  multi-tenant invariants configured in the backend.
- Run it against a running KIRP API instance with an admin-capable token.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx


SEED_PATH = Path(__file__).resolve().parent.parent / "seed" / "seed_definition.json"


def load_seed_definition() -> Dict[str, Any]:
  with SEED_PATH.open("r", encoding="utf-8") as f:
    return json.load(f)


def build_bootstrap_payload(seed: Dict[str, Any]) -> Dict[str, Any]:
  """
  Construct a payload compatible with POST /api/admin/bootstrap from the
  canonical seed definition.
  """
  tenants_seed = seed["tenants"]
  roles_seed = seed["roles"]

  # Simple deterministic bootstrap: we create one "bootstrap tenant" entry
  # per seed tenant, with minimal required fields. Users are generated with
  # role assignments based on the usersConfig hints.
  users_config = seed.get("usersConfig", {})
  users_per_tenant = users_config.get("users_per_tenant", {})
  min_users = int(users_per_tenant.get("min", 5))
  max_users = int(users_per_tenant.get("max", 10))

  # For initial bootstrap we keep things simple and generate min_users per tenant.
  # Additional synthetic users can be created later via separate tools if needed.
  roles_payload: List[Dict[str, Any]] = []
  for role in roles_seed:
    roles_payload.append(
      {
        "id": role["id"],
        "name": role["id"],
        "description": role.get("description", ""),
        "permissions": role.get("permissions", []),
      }
    )

  tenants_payload: List[Dict[str, Any]] = []
  spaces_payload: List[Dict[str, Any]] = []
  users_payload: List[Dict[str, Any]] = []

  for tenant in tenants_seed:
    tenant_id = tenant["id"]
    tenants_payload.append(
      {
        "id": tenant_id,
        "name": tenant["displayName"],
        "slug": tenant_id,
        "industry": tenant.get("industry"),
        "size": tenant.get("size"),
      }
    )
    for space in tenant.get("spaces", []):
      spaces_payload.append(
        {
          "id": f"{tenant_id}:{space['id']}",
          "tenant_id": tenant_id,
          "name": space["displayName"],
          "slug": space["id"],
          "purpose": space.get("purpose"),
        }
      )

    # Generate a small set of users per tenant.
    # We fix to min_users for determinism.
    for idx in range(min_users):
      user_id = f"{tenant_id}-user-{idx+1}"
      email = f"{user_id}@example.com"
      # Alternate roles for diversity.
      role = roles_seed[idx % len(roles_seed)]["id"]
      users_payload.append(
        {
          "id": user_id,
          "email": email,
          "name": f"{tenant['displayName']} User {idx+1}",
          "tenant_id": tenant_id,
          "role_ids": [role],
        }
      )

  return {
    "tenant": tenants_payload[0] if tenants_payload else {},
    "spaces": spaces_payload,
    "users": users_payload,
    "roles": roles_payload,
  }


async def run(base_url: str, token: str | None = None) -> None:
  seed = load_seed_definition()
  payload = build_bootstrap_payload(seed)

  headers: Dict[str, str] = {"Content-Type": "application/json"}
  if token:
    headers["Authorization"] = f"Bearer {token}"

  url = base_url.rstrip("/") + "/api/admin/bootstrap"
  async with httpx.AsyncClient(timeout=30.0) as client:
    resp = await client.post(url, json=payload, headers=headers)
    if resp.status_code >= 400:
      try:
        body = resp.json()
        print("Bootstrap error response:", body)
      except Exception:
        print("Bootstrap error body:", resp.text)
      resp.raise_for_status()
    print("Bootstrap response:", resp.json())


def main() -> None:
  import asyncio

  base_url = os.getenv("KIRP_API_BASE_URL", "http://localhost:8000")
  token = os.getenv("KIRP_API_TOKEN")
  asyncio.run(run(base_url=base_url, token=token))


if __name__ == "__main__":
  main()

