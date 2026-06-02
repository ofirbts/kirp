from __future__ import annotations


def redis_idempotency_key(tenant_id: str, logical_key: str) -> str:
    if not (tenant_id or "").strip() or (tenant_id or "").strip() == "*":
        raise ValueError("tenant_id required for idempotency key")
    tid = tenant_id.strip()
    return f"idempotency:{tid}:{logical_key}"
