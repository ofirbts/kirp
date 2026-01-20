# app/agent/agent.py
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from app.llm.client import get_llm
from app.rag.vector_store import get_vector_store
from app.core.persistence import PersistenceManager

logger = logging.getLogger(__name__)

class OmniAgent:
    def __init__(self, role: str = "general_assistant"):
        self.role = role
        self.llm = get_llm()

    async def _get_context(self, query: str) -> str:
        try:
            store = get_vector_store()
            docs = store.similarity_search(query, k=10)
            if not docs:
                return "No relevant past memories found."
            return "\n".join([f"- {d.page_content}" for d in docs])
        except Exception as e:
            logger.error(f"❌ Context retrieval failed: {e}")
            return "Context unavailable due to system error."

    async def process_task(
        self,
        task_description: str,
        user_id: str = "default",
        context_query: Optional[str] = None,
    ) -> str:
        memory = await PersistenceManager.get_agent_state(self.role)
        search_term = context_query if context_query else task_description
        context = await self._get_context(search_term)

        full_prompt = (
                    f"SYSTEM: You are the KIRP OS Core Intelligence (v7), a highly advanced neuro-symbolic agent.\n"
                    f"CORE PHILOSOPHY: You operate under the KIRP Contract. 1. No state mutation without an event. 2. All decisions must be explainable. 3. Zero hidden learning.\n"
                    f"ROLE: {self.role}\n"
                    f"CONTEXTUAL AWARENESS:\n"
                    f"- User ID: {user_id}\n"
                    f"- System Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                    f"- Active Capabilities: Hybrid RAG, Semantic Memory, Autonomous Planning.\n\n"
                    f"LONG-TERM KNOWLEDGE (Retrieved Context):\n{context}\n\n"
                    f"SHORT-TERM MEMORY (Last State):\n{memory}\n\n"
                    f"INSTRUCTIONS:\n"
                    f"1. ANALYZE the knowledge context before responding. If the context contains the answer, prioritize it.\n"
                    f"2. COGNITIVE TRACE: Briefly explain your reasoning if the task is complex.\n"
                    f"3. FORMAT: Use clear Markdown. Be professional, direct, and technically precise.\n"
                    f"4. LIMITATIONS: If the provided context is insufficient, state exactly what is missing.\n\n"
                    f"USER REQUEST: {task_description}\n\n"
                    f"RESPONSE:"
                )
        try:
            response = await self.llm.ainvoke(full_prompt)

            new_memory = {
                "last_task": task_description[:200],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await PersistenceManager.update_agent_state(self.role, new_memory)

            # Event ל־governance / observability
            await PersistenceManager.save_event(
                "agent_task_executed",
                {
                    "role": self.role,
                    "user_id": user_id,
                    "task": task_description[:500],
                    "context_query": context_query,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            return response.content
        except Exception as e:
            logger.error(f"Agent Execution Error: {e}")
            await PersistenceManager.save_event(
                "agent_task_failed",
                {
                    "role": self.role,
                    "user_id": user_id,
                    "task": task_description[:500],
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
            return f"Agent Error: {str(e)}"

agent = OmniAgent()
