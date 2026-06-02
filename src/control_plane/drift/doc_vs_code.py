from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def scan_control_plane_for_literal_wildcard_tenant(max_files: int = 200) -> list[str]:
    root = Path(__file__).resolve().parents[1]
    findings: list[str] = []
    count = 0
    for path in root.rglob("*.py"):
        if path.name == "doc_vs_code.py":
            continue
        if count >= max_files:
            break
        count += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        needle = 'tenant_id == "*"'
        if needle in text:
            findings.append(str(path.relative_to(repo_root())))
    return findings
