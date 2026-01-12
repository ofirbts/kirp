import logging
import asyncio
from datetime import datetime
from app.llm.client import get_llm
from app.core.persistence import PersistenceManager
from app.core.metrics import metrics
from app.rag.agent_rag import agent_rag_pipeline

logger = logging.getLogger(__name__)

class CoreAgent:
    def __init__(self):
        self.llm = get_llm()

    async def query(self, question: str):
        logger.info(f"CoreAgent processing: {question}")
        metrics.record_query() # רישום מטריקה ב-Redis
        
        now = datetime.now()
        current_time_info = now.strftime("%A, %H:%M, %d/%m/%Y")

        # 1. RAG Pipeline - שליפת זיכרון
        rag_result = await asyncio.to_thread(
            agent_rag_pipeline, 
            query=question, 
            session_id="default_user"
        )
        memories = rag_result.get("memories", [])
        context_str = "\n".join([str(m) for m in memories])
        
        # 2. בניית התשובה
        refine_prompt = f"""You are KIRP OS, Ofir's personal intelligence system.
        Current Time: {current_time_info}
        Context: {context_str}
        
        Answer in Hebrew, be concise and professional.
        """
        
        response = await self.llm.ainvoke([("system", refine_prompt), ("user", question)])
        final_answer = response.content

        # 3. זיהוי משימות ו-Governance (Multi-Agent Orchestration)
        if any(word in question.lower() for word in ["תזכיר", "צריך", "לקנות", "תקבע"]):
            event_id = PersistenceManager.append_event(
                event_type="task_identified",
                payload={"task": question, "suggested_action": "create_notion_task"},
                requires_approval=True # כאן נכנס ה-Enterprise Governance
            )
            logger.info(f"Task identified and held for approval. Event ID: {event_id}")

        return {
            "answer_text": final_answer,
            "sources": [{"text": m} for m in memories]
        }

    async def agent_query(self, text: str):
        res = await self.query(text)
        return {"answer": res["answer_text"]}

agent = CoreAgent()
