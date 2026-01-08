# app/agent/agent.py
from typing import Any, Dict, List, Optional

from app.rag.retriever import retrieve_context
from app.llm.client import get_llm
from app.services.memory import MemoryManager
from app.services.trace_logger import log_event
from app.core.persistence import PersistenceManager
from app.core.explainability import ExplanationBuilder
from app.core.metrics import Metrics
from app.core.policy import PolicyEngine, PolicyViolation
from app.services.knowledge import UnifiedKnowledgeStore
from app.core.self_eval import SelfEvaluator
from app.core.invariants import assert_invariant
from app.core.events import EventApplier
from app.core.observability import Observability
from app.agent.planner import PlannerAgent
from app.agent.executor import ExecutorAgent
from app.core.state_snapshot import StateSnapshotter


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
        self.snapshotter = StateSnapshotter(every_n_events=50)
        self.policy = PolicyEngine({
            # We use this policy when deciding whether to record something
            # into the agent's own internal memory.
            "update_memory": lambda p: len(str(p.get("content", ""))) < 10_000,
            "self_modify": lambda p: False,
        })

        self.knowledge = UnifiedKnowledgeStore()
        self.self_eval = SelfEvaluator()
        self.observability = Observability()
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()

        # This is the minimal agent state that we want to be able
        # to reconstruct via replay.
        self._state: Dict[str, Any] = {
            "total_queries": 0,
            "last_answer": None,
            "last_suggestions": [],
        }

    # ===== Persistence API =====

    def load_state(self, data: Dict[str, Any]) -> None:
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

    def reset(self) -> None:
        self._state = {
            "total_queries": 0,
            "last_answer": None,
            "last_suggestions": [],
        }
        # For replay we start with empty tiers – they will be repopulated
        # according to the events that are applied.
        self.memory = MemoryManager()

    # ===== Event-based replay API =====

    def apply_event(self, event: dict) -> None:
        """
        Apply a single persisted event back onto this agent instance.

        This is the core primitive used by replay scripts and potential
        higher-level debugging tools.
        """
        EventApplier().apply(self, event)

    # ===== Internal helpers =====

    def _record_internal_memory(self, kind: str, content: Dict[str, Any]) -> None:
        """
        Central place to push things into the agent's own MemoryManager,
        subject to policy, and emit events for deterministic replay.
        """
        try:
            self.policy.check("update_memory", {"content": content})
        except PolicyViolation:
            # If policy blocks the update – we simply skip.
            return

        tier_name = None

        if kind == "short":
            self.memory.short_term.add(content)
            tier_name = "short_term"
        elif kind == "mid":
            self.memory.mid_term.add(content)
            tier_name = "mid_term"
        elif kind == "long":
            self.memory.long_term.add(content)
            tier_name = "long_term"

        if tier_name is not None:
            PersistenceManager.append_event(
                "memory_add",
                {"tier": tier_name, "item": content},
            )

        # Let the tiers self-balance a bit.
        self.memory.promote()

    async def _execute_query(self, question: str) -> Dict[str, Any]:
        """
        Core agent decision logic, separated from the public API so that
        it can be called by an Executor (multi-agent split).
        """
        assert_invariant(question is not None, "Agent decision without question")

        self.metrics.inc("agent_decisions")
        self.observability.record_query()
        self.snapshotter.maybe_snapshot(self)


        memories = retrieve_context(question)
        llm = get_llm()

        # Observe retrieval scores (if present) for drift monitoring
        for m in memories:
            expl = m.get("explanation", {})
            score = expl.get("confidence")
            if isinstance(score, (int, float)):
                self.observability.record_score(float(score))

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

        PersistenceManager.append_event(
            "agent_counter",
            {"key": "total_queries", "value": self._state["total_queries"]},
        )

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

    # ===== Core behavior (public async API) =====

    async def agent_query(self, question: str) -> Dict[str, Any]:
        """
        Public entrypoint: delegates to planner + executor.
        """
        assert_invariant(question is not None, "Agent decision without question")

        plan = self.planner.plan(question)
        result = await self.executor.execute(plan, self)
        return result

    # ===== Synchronous agent path (legacy) =====

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

        PersistenceManager.append_event(
            "agent_counter",
            {"key": "total_queries", "value": self._state["total_queries"]},
        )

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
