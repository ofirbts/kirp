from typing import List, Dict, Any

class Deduplicator:
    """
    Very simple deduplicator for MemoryHub.
    Checks if content already exists exactly in recent memories.
    """

    def is_duplicate(self, content: str, recent: List[Dict[str, Any]]) -> bool:
        normalized = content.strip()
        for item in recent:
            text = (item.get("text") or "").strip()
            if text == normalized:
                return True
        return False
