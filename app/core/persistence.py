import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

BASE_PATH = "storage"
SESSIONS_PATH = os.path.join(BASE_PATH, "sessions")
AGENT_STATE_PATH = os.path.join(BASE_PATH, "agent_state")
EVENTS_PATH = os.path.join(BASE_PATH, "events")

for path in [SESSIONS_PATH, AGENT_STATE_PATH, EVENTS_PATH]:
    os.makedirs(path, exist_ok=True)


class PersistenceManager:
    # -------- Sessions --------

    @staticmethod
    def save_session(session_id: str, data: Dict[str, Any]) -> None:
        tmp_path = os.path.join(SESSIONS_PATH, f"{session_id}.tmp")
        final_path = os.path.join(SESSIONS_PATH, f"{session_id}.json")

        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        os.replace(tmp_path, final_path)

    @staticmethod
    def load_session(session_id: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(SESSIONS_PATH, f"{session_id}.json")
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def list_sessions() -> list[str]:
        return [
            f.replace(".json", "")
            for f in os.listdir(SESSIONS_PATH)
            if f.endswith(".json")
        ]

    # -------- Agent State --------

    @staticmethod
    def save_agent_state(state: Dict[str, Any]) -> None:
        path = os.path.join(AGENT_STATE_PATH, "agent.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    @staticmethod
    def load_agent_state() -> Optional[Dict[str, Any]]:
        path = os.path.join(AGENT_STATE_PATH, "agent.json")
        if not os.path.exists(path):
            return None

        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    # -------- Events --------

    @staticmethod
    def append_event(event_type: str, payload: Dict[str, Any]) -> str:
        event_id = str(uuid.uuid4())
        record = {
            "id": event_id,
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload,
        }

        path = os.path.join(EVENTS_PATH, "events.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return event_id

    @staticmethod
    def read_events(limit: int = 100) -> list[Dict[str, Any]]:
        path = os.path.join(EVENTS_PATH, "events.jsonl")
        if not os.path.exists(path):
            return []

        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        return [json.loads(line) for line in lines[-limit:]]
