from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.control_plane.orchestrator import preflight
from src.control_plane.runtime_guards.auth_guard import require_any_role
from src.control_plane.runtime_guards.event_guard import require_event_tenant
from src.control_plane.runtime_guards.tenant_guard import require_non_wildcard_tenant, require_same_tenant


def test_require_non_wildcard_tenant_rejects_star() -> None:
    with pytest.raises(HTTPException) as e:
        require_non_wildcard_tenant("*")
    assert e.value.status_code == 403


def test_require_same_tenant_mismatch() -> None:
    with pytest.raises(HTTPException) as e:
        require_same_tenant("a", "b")
    assert e.value.status_code == 403


def test_require_any_role_missing() -> None:
    with pytest.raises(HTTPException) as e:
        require_any_role(["user"], {"admin"})
    assert e.value.status_code == 403


def test_require_event_tenant_mismatch() -> None:
    with pytest.raises(HTTPException) as e:
        require_event_tenant({"tenant_id": "other"}, "mine")
    assert e.value.status_code == 403


def test_preflight_gate_user_present(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.auth.tenant_context import TenantContext

    monkeypatch.setattr(
        "src.control_plane.orchestrator.get_tenant_context",
        lambda _r: TenantContext(tenant_id="t1", space_id="s", user_id="", roles=[]),
    )
    with pytest.raises(HTTPException) as e:
        preflight(MagicMock())
    assert e.value.status_code == 403
    assert "gate_failed" in str(e.value.detail)
