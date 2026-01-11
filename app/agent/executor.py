# app/agent/executor.py
from typing import Dict, Any
import asyncio
from app.services.notion import notion  # הייבוא נשאר אותו דבר

class ExecutorAgent:
    async def execute(self, plan: Dict[str, Any], agent) -> Dict[str, Any]:
        query = plan.get("query", "")

        # 1️⃣ הרצה ישירה – async תקני
        result = await self._run_query_step(query, agent)

        # 2️⃣ רישום ב-Notion – כאן השינוי המרכזי!
        confidence = result.get("confidence", 1.0)
        trace_id = result.get("explanation_id", "gen-" + query[:10])

        # בדיקה אם השירות פעיל לפני הביצוע
        if notion.enabled():
            notion.create_task(
                title=f"Query: {query[:50]}...",
                trace_id=trace_id,
                source="Agent",
                confidence=confidence,
            )

        # 3️⃣ בדיקת אישורים - גם כאן כדאי להגן
        if notion.enabled():
            await self.process_approved_tasks()

        return result

    async def _run_query_step(self, query: str, agent) -> Dict[str, Any]:
        return await asyncio.wait_for(
            agent._execute_query(query),
            timeout=30
        )

    async def process_approved_tasks(self):
        # אין צורך לשנות את כל הלוגיקה כאן, 
        # כי ה-if notion.enabled() למעלה כבר מגן עלינו
        approved_tasks = notion.get_pending_approvals()
        
        for task in approved_tasks:
            # ... שאר הקוד שלך ללא שינוי ...
            properties = task.get("properties", {})
            # וכו'
            page_id = task["id"]
            notion.update_status(page_id, "Done")