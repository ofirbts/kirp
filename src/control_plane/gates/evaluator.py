from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.control_plane.gates.severity import Severity


@dataclass(frozen=True)
class Gate:
    gate_id: str
    severity: Severity
    check: Callable[[dict[str, Any]], bool]


def evaluate_gates(gates: list[Gate], context: dict[str, Any]) -> list[tuple[Gate, bool]]:
    return [(g, bool(g.check(context))) for g in gates]
