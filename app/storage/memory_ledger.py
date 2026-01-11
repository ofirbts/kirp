import json
from pathlib import Path
from typing import List, Dict

EVENTS_FILE = Path("storage/events/events.jsonl")

def load_all_memories(limit: int = 200) -> List[Dict]:
    memories = []
    if not EVENTS_FILE.exists():
        return memories

    with EVENTS_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                event = json.loads(line)
                if event.get("type") == "knowledge_add":
                    memories.append({
                        "content": event["payload"]["content"],
                        "source": event["payload"].get("source", "unknown"),
                        "timestamp": event["timestamp"],
                    })
            except Exception:
                continue

    return memories[-limit:]
