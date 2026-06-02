from __future__ import annotations

from typing import Any, Mapping


def replay_events_single_tenant(events: list[Mapping[str, Any]]) -> tuple[bool, str | None]:
    if not events:
        return True, None
    tenants = {str(e.get("tenant_id", "")).strip() for e in events}
    tenants.discard("")
    if len(tenants) > 1:
        return False, "mixed_tenant_replay"
    if len(tenants) == 0:
        return False, "missing_tenant"
    return True, None


def replay_events_ordered_ids(events: list[Mapping[str, Any]]) -> tuple[bool, str | None]:
    ids: list[str] = []
    for e in events:
        eid = e.get("id")
        if eid is None:
            continue
        ids.append(str(eid))
    if len(ids) <= 1:
        return True, None
    if ids != sorted(ids):
        return False, "out_of_order"
    return True, None
