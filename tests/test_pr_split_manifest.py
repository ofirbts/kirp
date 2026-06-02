from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import scripts.pr_split_manifest as manifest


def test_pr_scopes_defined() -> None:
    assert len(manifest.PR_SCOPES) == 5
    for scope, prefixes in manifest.PR_SCOPES.items():
        assert prefixes, scope


def test_classify_telemetry_file() -> None:
    hits = manifest.classify("src/telemetry/trace_health.py")
    assert "telemetry" in hits


def test_classify_embedding_to_trace_reconstruction() -> None:
    hits = manifest.classify("src/core/embedding_provider.py")
    assert "trace_reconstruction" in hits


def test_classify_unscoped_cursor_file() -> None:
    hits = manifest.classify(".cursor/rules/foo.mdc")
    assert hits == []


def test_manifest_runs_on_repo() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        ["python3", "scripts/pr_split_manifest.py"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert "pr_split_manifest:" in proc.stdout or "pr_split_manifest:" in proc.stderr
