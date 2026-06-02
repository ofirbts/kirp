from __future__ import annotations

import json
import os


def resolve_whatsapp_webhook_tenant(from_number: str | None = None) -> tuple[str, str, str]:
    default_tenant = os.getenv("WHATSAPP_WEBHOOK_TENANT_ID", "default").strip() or "default"
    default_space = os.getenv("WHATSAPP_WEBHOOK_SPACE_ID", "all").strip() or "all"
    default_user = os.getenv("WHATSAPP_WEBHOOK_USER_ID", "system").strip() or "system"
    raw_map = (os.getenv("WHATSAPP_WEBHOOK_TENANT_MAP") or "").strip()
    if raw_map and from_number:
        try:
            mapping = json.loads(raw_map)
            if isinstance(mapping, dict):
                entry = mapping.get(from_number) or mapping.get(from_number.lstrip("+"))
                if isinstance(entry, str) and entry.strip():
                    return entry.strip(), default_space, default_user
                if isinstance(entry, dict):
                    t = str(entry.get("tenant_id") or default_tenant).strip() or default_tenant
                    s = str(entry.get("space_id") or default_space).strip() or default_space
                    u = str(entry.get("user_id") or default_user).strip() or default_user
                    return t, s, u
        except json.JSONDecodeError:
            pass
    return default_tenant, default_space, default_user
