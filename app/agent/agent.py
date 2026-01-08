from typing import Any, Dict, List, Optional

from app.rag.retriever import retrieve_context
from app.llm.client import get_llm
from app.services.memory import MemoryManager
from app.services.trace_logger import log_event
from app.core.persistence import PersistenceManager
from app.core.explainability import ExplanationBuilder
from app.core.metrics import Metrics
from app.core.policy import PolicyEngine, PolicyViolation
from app.services.knowledge import KnowledgeStore
from app.core.self_eval import SelfEvaluator
from app.core.invariants import assert_invariant


AGENT_PROMPT = """
You are a proactive personal assistant.

Given the following memories:
{context}

Decide if there is an action you could help with.
If yes – suggest it politely.
If no – answer normally.
"""


class Agent:
    def __init__(self) -> None:
        self.explainer = ExplanationBuilder()
        self.memory = MemoryManager()
        self.metrics = Metrics()
        self.policy = PolicyEngine({
            # We use this policy when deciding whether to record something
            # into the agent's own internal memory.
            "update_memory": lambda p: len(str(p.get("content", ""))) < 10_000,
            "self_modify": lambda p: False,
        })

        self.knowledge = KnowledgeStore()
        self.self_eval = SelfEvaluator()

        # This is the minimal agent state that we want to be able
        # to reconstruct via replay.
        self._state: Dict[str, Any] = {
            "total_queries": 0,
            "last_answer": None,
            "last_suggestions": [],
        }

    # ===== Persistence API =====

    def load_state(self, data: Dict[str, Any]):
        # Defensive: tolerate partial / old snapshots.
        self._state = data.get("state", {
            "total_queries": 0,
            "last_answer": None,
            "last_suggestions": [],
        })
        self.memory.load(data.get("memory", {}))

    def dump_state(self) -> Dict[str, Any]:
        return {
            "state": self._state,
            "memory": self.memory.snapshot(),
        }

    # ===== Reset (for replay) =====

    def reset(self):
        self._state = {
            "total_queries": 0,
            "last_answer": None,
            "last_suggestions": [],
        }
        # For replay we start with empty tiers – they will be repopulated
        # according to the events that are applied.
        self.memory = MemoryManager()

    # ===== Apply decision (for replay) =====

    def apply_decision(self, payload: dict):
        """
        Re-apply an agent decision from a persisted event.

        Supports both:
        - "agent_sync_decision"/"agent_async_decision" payloads
          (with answer / suggestions / memory_count)
        - older "agent_decision" style payloads that may only contain
          query / intents / confidence / memories_used
        """
        self._state["total_queries"] += 1

        answer = payload.get("answer")
        if answer is not None:
            self._state["last_answer"] = answer

        suggestions = payload.get("suggestions")
        if suggestions is not None:
            self._state["last_suggestions"] = suggestions

        # We intentionally do not rebuild the full MemoryManager tiers here,
        # because the replay pipeline focuses on agent observable state,
        # not every intermediate retrieval result.

    # ===== Internal helpers =====

    def _record_internal_memory(self, kind: str, content: Dict[str, Any]) -> None:
        """
        Central place to push things into the agent's own MemoryManager,
        subject to policy.
        """
        try:
            self.policy.check("update_memory", {"content": content})
        except PolicyViolation:
            # If policy blocks the update – we simply skip.
            return

        if kind == "short":
            self.memory.short_term.add(content)
        elif kind == "mid":
            self.memory.mid_term.add(content)
        elif kind == "long":
            self.memory.long_term.add(content)

        # Let the tiers self-balance a bit.
        self.memory.promote()

    # ===== Core behavior =====

    async def agent_query(self, question: str) -> Dict[str, Any]:
        assert_invariant(question is not None, "Agent decision without question")

        self.metrics.inc("agent_decisions")

        memories = retrieve_context(question)
        llm = get_llm()

        context_str = "\n".join([m.get("text", "") for m in memories])

        response = await llm.apredict(
            AGENT_PROMPT.format(context=context_str)
        )

        answer = response
        suggestions: List[str] = []

        # Update internal memory with a concise trace of this decision
        self._record_internal_memory("short", {
            "type": "agent_async_decision",
            "query": question,
            "memories_used": len(memories),
            "answer_preview": str(answer)[:300],
        })

        # Update state
        self._state["total_queries"] += 1
        self._state["last_answer"] = answer
        self._state["last_suggestions"] = suggestions

        # Explainability event
        explanation = self.explainer.explain(
            reason="Agent async decision",
            inputs={"query": question, "memories": len(memories)},
            outcome={"answer": answer, "suggestions": suggestions},
        )
        explanation_id = PersistenceManager.append_event("explanation", explanation)

        # Persistence hook – detailed decision, used for replay
        decision_payload = {
            "question": question,
            "answer": answer,
            "suggestions": suggestions,
            "memory_count": len(memories),
            "explanation_id": explanation_id,
            "mode": "async",
        }
        PersistenceManager.append_event("agent_async_decision", decision_payload)

        return {
            "answer": answer,
            "sources": memories,
            "suggestions": suggestions,
            "agent_mode": True,
        }

    def run_agent(
        self,
        question: str,
        memories: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        assert_invariant(question is not None, "Agent decision without question")
        assert_invariant(memories is not None, "Agent decision without memories")

        self.metrics.inc("agent_decisions")

        if trace_id:
            log_event(trace_id, "agent_started", {"memory_count": len(memories)})

        top_text = memories[0].get("text", "") if memories else ""
        answer = f"Based on your memories, here's what I see: {top_text}"
        suggestions: List[str] = []

        if "price" in question.lower():
            suggestions.append(
                "Consider reviewing your pricing page and recent subscription changes."
            )

        # Update internal memory with a concise trace of this decision
        self._record_internal_memory("short", {
            "type": "agent_sync_decision",
            "query": question,
            "memories_used": len(memories),
            "answer_preview": str(answer)[:300],
        })

        # Update state
        self._state["total_queries"] += 1
        self._state["last_answer"] = answer
        self._state["last_suggestions"] = suggestions

        # Explainability event
        explanation = self.explainer.explain(
            reason="Agent sync decision",
            inputs={"query": question, "memories": len(memories)},
            outcome={"answer": answer, "suggestions": suggestions},
        )
        explanation_id = PersistenceManager.append_event("explanation", explanation)

        # Persistence hook – detailed decision, used for replay
        decision_payload = {
            "question": question,
            "answer": answer,
            "suggestions": suggestions,
            "memory_count": len(memories),
            "explanation_id": explanation_id,
            "mode": "sync",
        }
        PersistenceManager.append_event("agent_sync_decision", decision_payload)

        if trace_id:
            log_event(trace_id, "agent_decision", {
                "answer": answer,
                "suggestions": suggestions,
            })

        return {
            "answer": answer,
            "sources": memories,
            "suggestions": suggestions,
            "trace_id": trace_id,
            "agent_mode": True,
        }


agent = Agent()
