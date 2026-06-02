from __future__ import annotations

from typing import Any

from src.control_plane.gates.evaluator import Gate
from src.control_plane.gates.severity import Severity


def _tenant_present(ctx: dict[str, Any]) -> bool:
    t = ctx.get("tenant_id")
    return isinstance(t, str) and bool(t.strip()) and t.strip() != "*"


def _user_present(ctx: dict[str, Any]) -> bool:
    u = ctx.get("user_id")
    return isinstance(u, str) and bool(u.strip())


DEFAULT_PRODUCTION_GATES: list[Gate] = [
    Gate("tenant_present", Severity.BLOCK, _tenant_present),
    Gate("user_present", Severity.BLOCK, _user_present),
]
