#!/usr/bin/env python3
"""Detect drift between Next Action contract docs and monitoring implementation."""

from __future__ import annotations

from pathlib import Path
import re
import sys

DOC = Path("docs/next-action-contract.md")
MONITORING = Path("app/(dashboard)/monitoring/page.tsx")
ALLOWED_FAILURE_STATES = {"processing", "success", "failure", "network_issue"}


def fail(msg: str) -> int:
    print(f"contract_drift_check: FAIL: {msg}")
    return 1


def assert_contains(text: str, needle: str, label: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"missing {label}: {needle}")


def validate_setters(tsx: str, errors: list[str]) -> None:
    matches = re.findall(r'setFailureClarityState\(([^)]+)\)', tsx)
    for raw in matches:
        token = raw.strip().strip('"').strip("'")
        if token in {"null", "verifyStateFromVisibility(vis)", "nextState"}:
            continue
        if token not in ALLOWED_FAILURE_STATES:
            errors.append(f"unknown failure clarity state setter value: {raw}")


def main() -> int:
    if not DOC.exists():
        return fail("docs/next-action-contract.md missing")
    if not MONITORING.exists():
        return fail("monitoring page missing")

    doc = DOC.read_text(encoding="utf-8")
    tsx = MONITORING.read_text(encoding="utf-8")
    errors: list[str] = []

    # Contract table rows should remain explicit.
    for kind in ("failed", "partial", "processing", "completed", "idle"):
        assert_contains(doc, f"`{kind}`", f"doc kind {kind}", errors)

    # Required labels from contract.
    assert_contains(tsx, "Real action (mutates state)", "real action label", errors)
    assert_contains(tsx, "View-only (opens run context)", "view-only label", errors)
    assert_contains(tsx, "Guidance-only (no mutation)", "guidance label", errors)

    # Required fallback explicit text.
    assert_contains(
        tsx,
        "Action not available yet — opening flow",
        "explicit fallback copy",
        errors,
    )
    assert_contains(tsx, "Verifying action status...", "verify fallback stage copy", errors)
    assert_contains(tsx, "Verification timed out", "verify timeout copy", errors)
    assert_contains(tsx, "Fallback verify retry in progress", "verify fallback proof copy", errors)
    assert_contains(
        tsx,
        "Verify request timed out after fallback retry",
        "verify timeout proof copy",
        errors,
    )

    # Required execution mapping markers.
    assert_contains(tsx, 'case "failed"', "failed case branch", errors)
    assert_contains(tsx, 'case "partial"', "partial case branch", errors)
    assert_contains(tsx, 'case "processing"', "processing case branch", errors)
    assert_contains(tsx, 'case "completed"', "completed case branch", errors)
    assert_contains(tsx, 'case "idle"', "idle case branch", errors)
    assert_contains(tsx, "tryCreateTaskFromNextAction(", "task mutation call", errors)
    assert_contains(tsx, "beginRunContextForExecution(", "view fallback/open call", errors)

    # Failure states must be constrained.
    assert_contains(
        tsx,
        'type FailureClarityState = "processing" | "success" | "failure" | "network_issue";',
        "strict failure state type",
        errors,
    )
    assert_contains(
        tsx,
        "data-result-state={failureClarityState ?? undefined}",
        "visible failure state marker",
        errors,
    )
    validate_setters(tsx, errors)

    if errors:
        for e in errors:
            print(f"- {e}")
        return fail("drift detected")

    print("contract_drift_check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
