from typing import Any, Dict, List
from datetime import datetime

class MemoryTier:
    def __init__(self):
        self.items: List[Dict[str, Any]] = []

    def add(self, content: Any):
        self.items.append({
            "timestamp": datetime.utcnow().isoformat(),
            "content": content
        })

    def recent(self, limit: int = 5):
        return self.items[-limit:]


class MemoryManager:
    def __init__(self):
        self.short_term = MemoryTier()
        self.mid_term = MemoryTier()
        self.long_term = MemoryTier()

    def promote(self):
        if len(self.short_term.items) > 10:
            self.mid_term.add(self.short_term.items.pop(0))

    def snapshot(self):
        return {
            "short": self.short_term.items,
            "mid": self.mid_term.items,
            "long": self.long_term.items,
        }

    def load(self, data: dict):
        self.short_term.items = data.get("short", [])
        self.mid_term.items = data.get("mid", [])
        self.long_term.items = data.get("long", [])
