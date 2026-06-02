from __future__ import annotations

from src.control_plane.drift import scan_control_plane_for_literal_wildcard_tenant
from src.control_plane.drift.invariant_checker import run_invariants
from src.control_plane.drift.report import format_invariant_report


def test_run_invariants() -> None:
    results = run_invariants([("always_true", lambda: True), ("always_false", lambda: False)])
    assert results[0].ok and not results[1].ok
    text = format_invariant_report(results)
    assert "always_true: ok" in text
    assert "always_false: fail" in text


def test_scan_control_plane_returns_list() -> None:
    out = scan_control_plane_for_literal_wildcard_tenant()
    assert isinstance(out, list)
