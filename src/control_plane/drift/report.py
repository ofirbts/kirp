from __future__ import annotations

from src.control_plane.drift.invariant_checker import InvariantResult


def format_invariant_report(results: list[InvariantResult]) -> str:
    lines = [f"{r.name}: {'ok' if r.ok else 'fail'}" + (f" ({r.detail})" if r.detail else "") for r in results]
    return "\n".join(lines)
