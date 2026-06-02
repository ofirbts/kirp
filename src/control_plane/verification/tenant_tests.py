from __future__ import annotations

from typing import Any, Mapping


def document_tenant_matches(doc: Mapping[str, Any], ctx_tenant: str) -> bool:
    dt = doc.get("tenant_id")
    return isinstance(dt, str) and dt.strip() == ctx_tenant.strip()
