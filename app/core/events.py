# app/core/events.py
from typing import Dict, Any


class EventApplier:
    """
    Apply persisted events back onto an Agent instance.

    This is the core of deterministic replay: every mutation that the agent
    performs should have a corresponding event, and replay is just
    re-applying those events in order.
    """

    def apply(self, agent, event: Dict[str, Any]) -> None:
        etype = event["type"]
        payload = event["payload"]

        # Full-state snapshot (optional, not yet used heavily)
        if etype == "agent_state_snapshot":
            agent.load_state(payload["state"])
            return

        # Memory additions (short / mid / long)
        if etype == "memory_add":
            tier = payload["tier"]  # "short_term" / "mid_term" / "long_term"
            item = payload["item"]

            tier_obj = getattr(agent.memory, tier, None)
            if tier_obj is not None and hasattr(tier_obj, "items"):
                tier_obj.items.append(item)
            return

        # Memory promotion event (optional – only if emitted)
        if etype == "memory_promote":
            # We assume payload carries the promoted item and target tier.
            target_tier = payload.get("target_tier", "mid_term")
            item = payload["item"]

            tier_obj = getattr(agent.memory, target_tier, None)
            if tier_obj is not None and hasattr(tier_obj, "items"):
                tier_obj.items.append(item)
            return

        # Knowledge additions – routed through the agent's KnowledgeStore
        if etype == "knowledge_add":
            agent.knowledge.add(
                payload["content"],
                payload["source"],
                replaying=True,
            )
            return

        # Simple counters / scalar state fields
        if etype == "agent_counter":
            key = payload["key"]
            value = payload["value"]
            agent._state[key] = value
            return

        # Backward compatibility: re-apply decision events as "observable state"
        if etype in ("agent_sync_decision", "agent_async_decision"):
            agent._state["total_queries"] += 1
            agent._state["last_answer"] = payload.get("answer")
            agent._state["last_suggestions"] = payload.get("suggestions", [])
            return

        # Unknown types are ignored for now (forward compatibility).
        return
