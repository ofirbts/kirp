# app/rag/rag_engine.py
"""
KIRP RAG Engine v10
- אחראי על בניית תשובה מבוססת הקשר
- שליפת זיכרונות רלוונטיים (retriever)
- בניית prompt חכם
- קריאה ל‑LLM
- החזרת תשובה + הקשר + timestamp
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from app.rag.retriever import retrieve_context
from app.llm.client import get_llm

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    High‑level RAG engine:
    - Retrieve ranked memories
    - Build contextual prompt
    - Query LLM
    """

    def __init__(self):
        self.llm = get_llm()

    async def get_relevant_context(
        self,
        query: str,
        user_id: str,
        k: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        מחזיר רשימת זיכרונות מדורגים (text + metadata + ranking + explanation)
        """
        try:
            memories = await retrieve_context(query=query, user_id=user_id, k=k)
            return memories
        except Exception as e:
            logger.error(f"❌ RAG context retrieval failed: {e}")
            return []

    async def query(
        self,
        question: str,
        user_id: str,
        k: int = 6,
    ) -> Dict[str, Any]:
        """
        RAG מלא:
        1. Retrieve context
        2. Build prompt
        3. Query LLM
        4. Return answer + context
        """

        # 1. Retrieve context
        memories = await self.get_relevant_context(
            query=question,
            user_id=user_id,
            k=k,
        )

        # 2. Build context text
        context_text = "\n".join(
            f"- {m.get('text', '')}" for m in memories if m.get("text")
        )
        if not context_text.strip():
            context_text = "No relevant memories found."

        now_utc = datetime.now(timezone.utc).isoformat()

        # 3. Build prompt
        prompt = (
            f"Current Time (UTC): {now_utc}\n"
            f"User ID: {user_id}\n\n"
            f"Relevant Context:\n{context_text}\n\n"
            f"User Question:\n{question}\n\n"
            "You are KIRP OS Intelligence.\n"
            "Use the context when relevant.\n"
            "If the context is not helpful, answer from general knowledge.\n"
            "Be precise, structured, and helpful.\n"
        )

        # 4. Query LLM
        try:
            res = await self.llm.ainvoke(prompt)
            answer = res.content if hasattr(res, "content") else str(res)
        except Exception as e:
            logger.error(f"❌ LLM RAG error: {e}")
            answer = f"RAG Engine Error: {str(e)}"

        return {
            "answer": answer,
            "context": memories,
            "timestamp_utc": now_utc,
        }


# Singleton instance
rag_engine = RAGEngine()
