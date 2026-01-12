# app/core/events.py
from typing import Dict, Any
from datetime import datetime
import uuid
from app.core.persistence import PersistenceManager

class EventManager:
    """
    The Active side: Emits new events into the system.
    """
    @staticmethod
    def emit(event_type: str, payload: Dict[str, Any]):
        """
        Record a new event and save it to persistent storage.
        """
        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # בניית האובייקט המאוחד
        full_event = {
            "id": event_id,
            "type": event_type,
            "timestamp": timestamp,
            "payload": payload
        }
        
        # שמירה ל-DB / JSONL
        PersistenceManager.append_event(event_type, payload)
        
        print(f"📢 Event Emitted: {event_type}")
        return full_event

class EventApplier:
    """
    The Passive side: Apply persisted events back onto an Agent instance.
    (הקוד המקורי שלך נשמר כאן במלואו)
    """
    def apply(self, agent, event: Dict[str, Any]) -> None:
        etype = event["type"]
        payload = event["payload"]

        if etype == "agent_state_snapshot":
            agent.load_state(payload["state"])
            return

        if etype == "memory_add":
            tier = payload["tier"]
            item = payload["item"]
            tier_obj = getattr(agent.memory, tier, None)
            if tier_obj is not None and hasattr(tier_obj, "items"):
                tier_obj.items.append(item)
            return

        if etype == "memory_promote":
            target_tier = payload.get("target_tier", "mid_term")
            item = payload["item"]
            tier_obj = getattr(agent.memory, target_tier, None)
            if tier_obj is not None and hasattr(tier_obj, "items"):
                tier_obj.items.append(item)
            return

        if etype == "knowledge_add":
            agent.knowledge.add(
                payload["content"],
                payload["source"],
                replaying=True,
            )
            return

        if etype == "agent_counter":
            key = payload["key"]
            value = payload["value"]
            agent._state[key] = value
            return

        if etype in ("agent_sync_decision", "agent_async_decision"):
            agent._state["total_queries"] += 1
            agent._state["last_answer"] = payload.get("answer")
            agent._state["last_suggestions"] = payload.get("suggestions", [])
            return

        return