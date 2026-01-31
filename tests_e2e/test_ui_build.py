"""E2E: If brand_os_ui exists, validate package.json and next.config.js exist; optional build check."""
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
UI_DIR = REPO / "brand_os_ui"


@pytest.mark.skipif(not UI_DIR.is_dir(), reason="brand_os_ui not present")
def test_brand_os_ui_package_json_exists() -> None:
    assert (UI_DIR / "package.json").is_file()


@pytest.mark.skipif(not UI_DIR.is_dir(), reason="brand_os_ui not present")
def test_brand_os_ui_next_config_exists() -> None:
    assert (UI_DIR / "next.config.js").is_file()


@pytest.mark.skipif(not UI_DIR.is_dir(), reason="brand_os_ui not present")
def test_brand_os_ui_app_dir_exists() -> None:
    assert (UI_DIR / "app").is_dir()


@pytest.mark.skipif(not UI_DIR.is_dir(), reason="brand_os_ui not present")
def test_brand_os_ui_has_pages() -> None:
    app_dir = UI_DIR / "app"
    assert (app_dir / "page.tsx").exists() or (app_dir / "page.jsx").exists()
    assert (app_dir / "layout.tsx").exists() or (app_dir / "layout.jsx").exists()
