import json
from pathlib import Path

SNAPSHOT_PATH = Path("storage/state_snapshot.json")


def save_snapshot(state: dict):
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_PATH.write_text(json.dumps(state, indent=2))


def load_snapshot():
    if SNAPSHOT_PATH.exists():
        return json.loads(SNAPSHOT_PATH.read_text())
    return None
