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
from app.agent.critic import CriticAgent
from app.agent.verifier import VerifierAgent

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
            "update_memory": lambda p: len(str(p.get("content", ""))) < 10_000,
            "self_modify": lambda p: False,
        })
        self.critic = CriticAgent()
        self.verifier = VerifierAgent()

        self.knowledge = UnifiedKnowledgeStore()
        self.self_eval = SelfEvaluator()
        self.observability = Observability()
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()

        self._state: Dict[str, Any] = {
            "total_queries": 0,
            "last_answer": None,
            "last_suggestions": [],
        }

    # ===== Persistence API =====

    def load_state(self, data: Dict[str, Any]) -> None:
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
        self.memory = MemoryManager()

    # ===== Event-based replay API =====

    def apply_event(self, event: dict) -> None:
        EventApplier().apply(self, event)

    # ===== NEW: The missing query function =====
    def query(self, text: str):
        """
        Public synchronous wrapper for the RAG pipeline.
        Used by Orchestrator and Negotiation engines.
        """
        from app.rag.agent_rag import agent_rag_pipeline
        result = agent_rag_pipeline(text)
        return result.get("answer", "No answer found.")

    # ===== Internal helpers =====

    def _record_internal_memory(self, kind: str, content: Dict[str, Any]) -> None:
        try:
            self.policy.check("update_memory", {"content": content})
        except PolicyViolation:
            return

        content["memory_plane"] = "session"
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
        self.memory.promote()

    async def _execute_query(self, question: str) -> Dict[str, Any]:
        assert_invariant(question is not None, "Agent decision without question")

        self.metrics.inc("agent_decisions")
        self.observability.record_query()

        memories = retrieve_context(question)
        llm = get_llm()

        confidence = 0.0
        for m in memories:
            expl = m.get("explanation", {})
            score = expl.get("confidence")
            if isinstance(score, (int, float)):
                self.observability.record_score(float(score))
                confidence = max(confidence, float(score))

        context_str = "\n".join([m.get("text", "") for m in memories])
        response = await llm.apredict(AGENT_PROMPT.format(context=context_str))

        answer = response
        suggestions: List[str] = []

        self._record_internal_memory("short", {
            "type": "agent_async_decision",
            "query": question,
            "memories_used": len(memories),
            "answer_preview": str(answer)[:300],
        })

        self._state["total_queries"] += 1
        self._state["last_answer"] = answer
        self._state["last_suggestions"] = suggestions

        PersistenceManager.append_event(
            "agent_counter",
            {"key": "total_queries", "value": self._state["total_queries"]},
        )

        explanation = self.explainer.explain(
            reason="Agent async decision",
            inputs={"query": question, "memories": len(memories)},
            outcome={"answer": answer, "suggestions": suggestions},
        )
        explanation["confidence"] = confidence
        explanation_id = PersistenceManager.append_event("explanation", explanation)

        decision_payload = {
            "question": question,
            "answer": answer,
            "suggestions": suggestions,
            "memory_count": len(memories),
            "explanation_id": explanation_id,
            "mode": "async",
            "confidence": confidence,
        }
        PersistenceManager.append_event("agent_async_decision", decision_payload)

        critique = self.critic.critique(answer)
        verification = self.verifier.verify(answer, memories)

        return {
            "answer": answer,
            "sources": memories,
            "suggestions": suggestions,
            "critique": critique,
            "verification": verification,
            "agent_mode": True,
        }

    async def agent_query(self, question: str) -> Dict[str, Any]:
        assert_invariant(question is not None, "Agent decision without question")
        plan = self.planner.plan(question)
        result = await self.executor.execute(plan, self)
        return result

    def run_agent(self, question: str, memories: List[Dict[str, Any]], trace_id: Optional[str] = None) -> Dict[str, Any]:
        assert_invariant(question is not None, "Agent decision without question")
        assert_invariant(memories is not None, "Agent decision without memories")
        self.metrics.inc("agent_decisions")
        
        top_text = memories[0].get("text", "") if memories else ""
        answer = f"Based on your memories, here's what I see: {top_text}"
        suggestions: List[str] = []

        self._record_internal_memory("short", {
            "type": "agent_sync_decision",
            "query": question,
            "memories_used": len(memories),
        })

        self._state["total_queries"] += 1
        PersistenceManager.append_event("agent_async_decision", {"question": question, "answer": answer})

        return {"answer": answer, "sources": memories, "suggestions": suggestions, "agent_mode": True}

agent = Agent()