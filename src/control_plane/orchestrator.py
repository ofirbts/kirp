from __future__ import annotations

from fastapi import HTTPException, Request, status

from src.auth.tenant_context import TenantContext, get_tenant_context
from src.control_plane.gates.evaluator import Gate, evaluate_gates
from src.control_plane.gates.production_gates import DEFAULT_PRODUCTION_GATES
from src.control_plane.gates.severity import Severity
from src.control_plane.runtime_guards.auth_guard import require_any_role
from src.control_plane.runtime_guards.tenant_guard import require_non_wildcard_tenant


def resolve_context(request: Request) -> TenantContext:
    return get_tenant_context(request)


def preflight(
    request: Request,
    *,
    required_roles: set[str] | None = None,
    gates: list[Gate] | None = None,
) -> TenantContext:
    ctx = get_tenant_context(request)
    require_non_wildcard_tenant(ctx.tenant_id)
    if required_roles:
        require_any_role(ctx.roles, required_roles)
    glist = gates if gates is not None else DEFAULT_PRODUCTION_GATES
    ctx_dict: dict[str, object] = {
        "tenant_id": ctx.tenant_id,
        "user_id": ctx.user_id,
        "space_id": ctx.space_id,
        "roles": ctx.roles,
    }
    for gate, ok in evaluate_gates(glist, ctx_dict):
        if not ok and gate.severity == Severity.BLOCK:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"gate_failed:{gate.gate_id}",
            )
    return ctx
