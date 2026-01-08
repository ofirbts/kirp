# app/core/self_eval.py
from typing import Dict, Any


class SelfEvaluator:
    """
    Simple self-evaluation mechanism that looks at the persisted agent state
    and decides whether we should prune some memory tiers.

    It is intentionally conservative – it only triggers pruning when there is
    a clear sign of growth.
    """

    def evaluate(self, agent_state: dict) -> dict:
        score = 0.0

        memory: Dict[str, Any] = agent_state.get("memory", {})
        short_mem = memory.get("short", []) or []

        # Penalize if short-term memory grew too large.
        if len(short_mem) > 5:
            score -= 0.1

        # If the agent tracks errors in its state, we treat that as a signal
        # that something may be off.
        state_block = agent_state.get("state", {}) or agent_state
        if "errors" in state_block:
            score -= 0.2

        return {
            "score": round(score, 3),
            "recommendation": "prune_short_term" if score < 0 else "ok",
        }
