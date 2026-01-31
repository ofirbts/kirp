"""
Load Brand OS v3 config and agent definitions from brand_os_v3/config/ and brand_os_v3/agents/.
"""

import json
from pathlib import Path
from typing import Any

# Base path: sibling of brand_os_sdk package (repo root), then brand_os_v3
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_BASE = _REPO_ROOT / "brand_os_v3"


def _base_path() -> Path:
    import os
    return Path(os.environ.get("BRAND_OS_V3_PATH", str(_DEFAULT_BASE)))


def _read_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_identity(base: Path | None = None) -> dict[str, Any]:
    """Load Master Identity Core from config/00_Master_Identity_Core.json."""
    root = base or _base_path()
    return _read_json(root / "config" / "00_Master_Identity_Core.json")


def load_voice(base: Path | None = None) -> dict[str, Any]:
    """Load Voice Engine from config/03_Voice_Engine.json."""
    root = base or _base_path()
    return _read_json(root / "config" / "03_Voice_Engine.json")


def list_agents(base: Path | None = None) -> list[str]:
    """List agent IDs from brand_os_v3/agents/ (JSON filenames without .json)."""
    root = base or _base_path()
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return []
    return sorted(
        f.stem for f in agents_dir.glob("*.json")
    )
