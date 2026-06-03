from __future__ import annotations

import json
import os


def resolve_env_webhook_tenant(
    *,
    tenant_env: str,
    space_env: str,
    user_env: str,
    map_env: str | None,
    routing_key: str | None = None,
) -> tuple[str, str, str]:
    default_tenant = os.getenv(tenant_env, "default").strip() or "default"
    default_space = os.getenv(space_env, "all").strip() or "all"
    default_user = os.getenv(user_env, "system").strip() or "system"
    raw_map = (os.getenv(map_env) or "").strip() if map_env else ""
    if raw_map and routing_key:
        try:
            mapping = json.loads(raw_map)
            if isinstance(mapping, dict):
                entry = mapping.get(routing_key)
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


def resolve_slack_webhook_tenant(team_id: str | None = None) -> tuple[str, str, str]:
    return resolve_env_webhook_tenant(
        tenant_env="SLACK_WEBHOOK_TENANT_ID",
        space_env="SLACK_WEBHOOK_SPACE_ID",
        user_env="SLACK_WEBHOOK_USER_ID",
        map_env="SLACK_WEBHOOK_TENANT_MAP",
        routing_key=(team_id or "").strip() or None,
    )


def resolve_notion_webhook_tenant(workspace_id: str | None = None) -> tuple[str, str, str]:
    return resolve_env_webhook_tenant(
        tenant_env="NOTION_WEBHOOK_TENANT_ID",
        space_env="NOTION_WEBHOOK_SPACE_ID",
        user_env="NOTION_WEBHOOK_USER_ID",
        map_env="NOTION_WEBHOOK_TENANT_MAP",
        routing_key=(workspace_id or "").strip() or None,
    )
