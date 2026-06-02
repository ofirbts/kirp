from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class InvariantResult:
    name: str
    ok: bool
    detail: str | None = None


def run_invariants(checks: list[tuple[str, Callable[[], bool]]]) -> list[InvariantResult]:
    out: list[InvariantResult] = []
    for name, fn in checks:
        try:
            ok = bool(fn())
        except Exception as e:
            out.append(InvariantResult(name=name, ok=False, detail=str(e)))
            continue
        out.append(InvariantResult(name=name, ok=ok, detail=None if ok else "failed"))
    return out
