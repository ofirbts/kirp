# app/services/list_service.py
"""
KIRP List Service v4
Handles:
- Extracting lists from user text
- Normalizing list items
- Persisting list events
- Optional: saving as memory items
"""

import re
from typing import List, Dict, Any

from app.core.persistence import PersistenceManager
from app.core.observability import Observability, TraceContext


class ListService:
    """
    High-level list extraction + persistence.
    """

    @staticmethod
    def extract_list(text: str) -> List[str]:
        """
        Extract bullet-like items from text.
        Supports:
        - Lines starting with "-", "*", "•"
        - Numbered lists: "1. item"
        - Raw lines separated by newline
        """

        lines = text.split("\n")
        items = []

        for line in lines:
            clean = line.strip()

            # Bullet formats
            if clean.startswith(("-", "*", "•")):
                items.append(clean[1:].strip())
                continue

            # Numbered formats
            if re.match(r"^\d+[\.\)]\s+", clean):
                items.append(re.sub(r"^\d+[\.\)]\s+", "", clean))
                continue

            # Fallback: treat non-empty lines as items
            if clean:
                items.append(clean)

        # Remove empty items
        return [i for i in items if i.strip()]

    @staticmethod
    async def save_list(
        user_id: str,
        raw_text: str,
        items: List[str],
        ctx: TraceContext | None = None,
    ) -> Dict[str, Any]:
        """
        Persist list creation event.
        """

        event_data = {
            "user_id": user_id,
            "raw_text": raw_text,
            "items": items,
        }

        await Observability.event(
            event_type="list_created",
            data=event_data,
            ctx=ctx,
        )

        return {
            "status": "ok",
            "count": len(items),
            "items": items,
        }

    @staticmethod
    async def process_list(
        text: str,
        user_id: str,
        ctx: TraceContext | None = None,
    ) -> Dict[str, Any]:
        """
        Full pipeline:
        - Extract list
        - Persist event
        - Return normalized list
        """

        items = ListService.extract_list(text)

        return await ListService.save_list(
            user_id=user_id,
            raw_text=text,
            items=items,
            ctx=ctx,
        )
