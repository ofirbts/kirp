# app/agent/agent.py
import logging
import json
import os
from datetime import datetime, timezone
from typing import Optional

from app.llm.client import get_llm
from app.rag.vector_store import get_vector_store
from app.core.persistence import PersistenceManager
from app.services.notion.notion_impl import NotionClient
import asyncio

logger = logging.getLogger(__name__)


class OmniAgent:
    """
    High-level conversational + reasoning agent.
    Uses:
    - LLM (via get_llm)
    - RAG (via Qdrant vector store)
    - PersistenceManager for events & state

    This is the main agent used by:
    - app/ui/api.py (ask)
    - future channels (WhatsApp, etc.)
    """

    def __init__(self, role: str = "general_assistant"):
        self.role = role
        self.llm = get_llm()

    async def _get_context(self, query: str, user_id: str) -> str:
        """
        שליפת הקשר מה-Vector Store (k קטן כדי לשמור על מהירות ודיוק).
        """
        try:
            store = get_vector_store()
            # similarity_search הוא סינכרוני, אבל זה בסדר בתוך async
            docs = store.similarity_search(query, k=3, filter={"user_id": user_id})
        except TypeError:
            # במקרה שה-filter לא נתמך בחתימה הזו (תאימות לאחור)
            try:
                docs = store.similarity_search(query, k=3)
            except Exception as e:
                logger.error(f"🧠 Context retrieval failed (no filter): {e}")
                return "Context unavailable due to system error."

        if not docs:
            return "No relevant past memories found."

        return "\n".join([f"- {d.page_content}" for d in docs])

    async def process_task(
        self,
        task_description: str,
        user_id: str = "default",
        context_query: Optional[str] = None,
    ) -> str:
        """
        Main entrypoint for user tasks:
        - Loads persona (if exists)
        - Fetches RAG context
        - Builds system prompt
        - Invokes LLM
        - Persists event + agent state
        """
        # Persona
        persona_path = f"data/profiles/user_{user_id}_persona.json"
        if os.path.exists(persona_path):
            try:
                with open(persona_path, "r", encoding="utf-8") as f:
                    persona = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load persona for {user_id}: {e}")
                persona = {
                    "name": user_id,
                    "tone": "professional",
                    "instructions": "Be a helpful assistant.",
                }
        else:
            persona = {
                "name": user_id,
                "tone": "professional",
                "instructions": "Be a helpful assistant.",
            }

        search_term = context_query if context_query else task_description
        context = await self._get_context(search_term, user_id=user_id)

        full_prompt = (
            f"SYSTEM: You are KIRP OS Core Intelligence.\n"
            f"TARGET USER: {persona['name']}\n"
            f"YOUR TONE: {persona['tone']}\n"
            f"SPECIFIC INSTRUCTIONS FOR THIS USER: {persona['instructions']}\n"
            f"PHILOSOPHY: No state mutation without event, explainable decisions.\n\n"
            f"CONTEXTUAL AWARENESS:\n"
            f"- User ID: {user_id}\n"
            f"- System Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
            f"LONG-TERM KNOWLEDGE (RAG):\n{context}\n\n"
            f"USER REQUEST: {task_description}\n\n"
            f"RESPONSE:"
        )

        try:
            response = await self.llm.ainvoke(full_prompt)

            # Update agent state (simple last_task memory)
            new_memory = {
                "last_task": task_description[:200],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await PersistenceManager.update_agent_state(self.role, new_memory)

            # Persist event
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

            return response.content if hasattr(response, "content") else str(response)

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


class CoreAgent:
    """
    Background worker for system-level tasks (e.g., Notion sync).
    Runs in a loop and processes pending improvements / config changes.
    """

    def __init__(self):
        self.notion = NotionClient()
        self.active = True

    async def run_worker(self):
        logger.info("🤖 CoreAgent: Background Sync System Online")
        while self.active:
            try:
                # משיכת משימות שממתינות ל-Notion
                pending = await PersistenceManager.get_pending_improvements()
                for task in pending:
                    if task.get("type") == "notion_sync":
                        success = await self._sync_to_notion(task)
                        if success:
                            await PersistenceManager.apply_config_change(task["_id"])

                # בדיקה כל 20 שניות
                await asyncio.sleep(20)
            except Exception as e:
                logger.error(f"CoreAgent Loop Error: {e}")
                await asyncio.sleep(5)

    async def _sync_to_notion(self, task: dict) -> bool:
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(
                None,
                self.notion.create_task,
                task.get("content", "New Task"),
                str(task.get("_id")),
                "KIRP-Automator",
            )
        except Exception as e:
            logger.error(f"Notion sync failed for task {task.get('_id')}: {e}")
            return False


# Instances for import
agent = OmniAgent()
system_agent = CoreAgent()
