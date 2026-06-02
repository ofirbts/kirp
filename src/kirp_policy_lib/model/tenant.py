from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str | None
    provenance: str

    @staticmethod
    def absent() -> TenantContext:
        return TenantContext(None, "absent")


def _norm_headers(h: Mapping[str, Any] | None) -> dict[str, str]:
    if not h:
        return {}
    out: dict[str, str] = {}
    for k, v in h.items():
        if v is None:
            continue
        out[str(k).strip().lower()] = str(v).strip()
    return out


def _pick_str(d: Mapping[str, Any] | None, key: str) -> tuple[str | None, str]:
    if not d:
        return None, "none"
    v = d.get(key)
    if isinstance(v, str):
        s = v.strip()
        if s:
            return s, f"field:{key}"
    return None, "none"


def extract_tenant_id(request_like: Mapping[str, Any]) -> str | None:
    return resolve_tenant_context(request_like).tenant_id


def resolve_tenant_context(request_like: Mapping[str, Any]) -> TenantContext:
    t, src = _pick_str(request_like, "tenant_id")
    if t:
        return TenantContext(t, f"top_level:{src}")
    for key in ("auth", "jwt", "token", "claims"):
        nested = request_like.get(key)
        if isinstance(nested, Mapping):
            t2, _ = _pick_str(nested, "tenant_id")
            if t2:
                return TenantContext(t2, key)
    headers = _norm_headers(request_like.get("headers") if isinstance(request_like.get("headers"), Mapping) else None)
    for hk in ("x-tenant-id", "x-kirp-tenant-id", "x-tenant"):
        if hk in headers and headers[hk]:
            return TenantContext(headers[hk], hk)
    body = request_like.get("body")
    if isinstance(body, Mapping):
        t3, _ = _pick_str(body, "tenant_id")
        if t3:
            return TenantContext(t3, "body")
    return TenantContext.absent()
