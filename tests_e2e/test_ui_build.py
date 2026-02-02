"""E2E: Validate unified KIRP UI (Next.js app at repo root)."""
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_unified_ui_package_json_exists() -> None:
    assert (REPO / "package.json").is_file()


def test_unified_ui_next_config_exists() -> None:
    assert (REPO / "next.config.js").is_file()


def test_unified_ui_app_dir_exists() -> None:
    assert (REPO / "app").is_dir()


def test_unified_ui_has_pages() -> None:
    app_dir = REPO / "app"
    assert (app_dir / "page.tsx").exists() or (app_dir / "page.jsx").exists()
    assert (app_dir / "layout.tsx").exists() or (app_dir / "layout.jsx").exists()


def test_unified_ui_dashboard_routes_exist() -> None:
    dashboard = REPO / "app" / "(dashboard)"
    assert dashboard.is_dir()
    for name in ["dashboard", "mission-control", "agents", "run"]:
        assert (dashboard / name / "page.tsx").exists() or (dashboard / name / "page.jsx").exists()
