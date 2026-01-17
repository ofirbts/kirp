import logging
from datetime import datetime, timezone
from typing import List, Dict, Any

class EventStoryteller:
    """Translates raw events into human-readable insights for the UI."""
    
    @staticmethod
    def tell_story(event: Dict[str, Any]) -> Dict[str, str]:
        etype = event.get("type")
        payload = event.get("payload", {})
        ts = event.get("timestamp", "")
        
        # המרת זמן לפורמט קריא
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M")
        except:
            time_str = "Recently"

        stories = {
            "knowledge_add": f"🧠 תייקתי תובנה חדשה: '{payload.get('content', '')[:40]}...'",
            "memory_add": f"🧠 זיכרון חדש נשמר במערכת.",
            "task_add": f"✅ יצרתי משימה חדשה: '{payload.get('text', '')}'",
            "intent_detected": f"🧭 זיהיתי כוונה מסוג {payload.get('intent')}",
            "query_executed": f"🔍 חיפשתי תשובה בנושא '{payload.get('query', '')[:30]}...'"
        }

        return {
            "story": stories.get(etype, f"System Action: {etype}"),
            "time": time_str,
            "icon": "✨" if etype == "knowledge_add" else "⚙️"
        }