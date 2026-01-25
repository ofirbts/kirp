# app/core/event_storyteller.py
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional 
from app.core.persistence import PersistenceManager 
logger = logging.getLogger("KIRP-Observability")

class EventStoryteller:
    """
    Converts raw system events into human-readable stories for the UI.
    """

    @staticmethod
    def tell_story(event: Dict[str, Any]) -> Dict[str, str]:
        etype = event.get("type")
        payload = event.get("payload", {})
        ts = event.get("timestamp", "")

        # Format timestamp
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M")
        except Exception:
            time_str = "Recently"

        stories = {
            "knowledge_add": f"🧩 נוספה ידיעה חדשה: '{payload.get('content', '')[:40]}...'",
            "memory_add": "🧠 נוספה פיסת זיכרון חדשה למערכת.",
            "task_add": f"📝 נוצרה משימה חדשה: '{payload.get('text', '')}'",
            "intent_detected": f"🎯 זוהתה כוונה: {payload.get('intent')}",
            "query_executed": f"🔍 בוצע חיפוש עבור '{payload.get('query', '')[:30]}...'",
        }

        return {
            "story": stories.get(etype, f"System Action: {etype}"),
            "time": time_str,
            "icon": "🧩" if etype == "knowledge_add" else "✨",
        }

class TraceContext:
    def __init__(self, user_id: Optional[str] = None, source: str = "system"):
        self.trace_id = f"trace_{uuid.uuid4().hex[:10]}"
        self.user_id = user_id
        self.source = source
        self.started_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "source": self.source,
            "started_at": self.started_at,
        }


class Observability:
    @staticmethod
    def new_trace(user_id: Optional[str] = None, source: str = "system"):
        return TraceContext(user_id=user_id, source=source)

    @staticmethod
    def log(message: str, ctx: Optional[TraceContext] = None, **extra):
        logger.info(
            message,
            extra={
                "trace": ctx.to_dict() if ctx else None,
                "extra": extra,
            },
        )

    @staticmethod
    async def event(event_type: str, data: Dict[str, Any], ctx: Optional[TraceContext] = None):
        enriched = {
            **data,
            "trace_id": ctx.trace_id if ctx else None,
            "source": ctx.source if ctx else "system",
        }
        await PersistenceManager.append_event(event_type, enriched)