import logging
import asyncio
from datetime import datetime, timezone
from app.llm.client import get_llm
from app.core.persistence import PersistenceManager

logger = logging.getLogger(__name__)

class CoreAgent:
    def __init__(self):
        self.llm = get_llm()

    async def query(self, question: str, user_id: str):
        # 1. שליפת אירועים רלוונטיים - שימוש ב-Thread כדי לא לחסום את ה-Event Loop
        raw_events = await asyncio.to_thread(PersistenceManager.get_user_events, user_id=user_id, limit=50)
        
        processed_context_parts = []
        now = datetime.now(timezone.utc)


        for e in raw_events:
            importance = e.get("importance", 1)
            try:
                # תמיכה גם במחרוזת וגם באובייקט datetime
                ts = e["timestamp"]
                timestamp = datetime.fromisoformat(ts) if isinstance(ts, str) else ts
            except:
                timestamp = now
                
            days_passed = (now - timestamp).days
            effective_score = importance - (days_passed * 0.1)
            
            if effective_score > 0:
                e_type = e.get('type', '')
                data = e.get('data', {})
                
                if e_type == 'knowledge_add':
                    content = data.get('text', '')
                    processed_context_parts.append(f"[מידע - רלוונטיות {effective_score:.1f}]: {content}")
                elif e_type == 'task_identified':
                    task = data.get('task', '')
                    processed_context_parts.append(f"[משימה פתוחה]: {task}")

        context_str = "\n".join(processed_context_parts)

        # 2. ה-Prompt המשודרג
        refine_prompt = f"""
        אתה KIRP OS, ה-AI האישי של {user_id}. 
        אם המשתמש הוא אופיר בטש: הוא מנהל פרויקטים מנוסה (10+ שנים) עם לב ענק, איש של אמונה וערכים.
        
        הקשר נוכחי מזיכרון המשתמש:
        {context_str}
        
        הנחיות:
        1. חבר נקודות בין טכנולוגיה (Docker, RAG) לערכים אישיים.
        2. תעדוף משימות טריות.
        3. שפה: עברית רהוטה, חמה ומקצועית.
        """

        response = await self.llm.ainvoke([("system", refine_prompt), ("user", question)])
        # 2.5 לוג החלטת סוכן (Agent Decision Trace)
        try:
            await asyncio.to_thread(
                PersistenceManager.append_event,
                user_id,
                "agent_decision",
                {
                    "query": question,
                    "answer_preview": response.content[:500],
                    "memories_used": len(processed_context_parts),
                    "timestamp": datetime.now(timezone.utc).isoformat()

                }
            )
        except Exception as e:
            logger.warning(f"Agent decision log failed: {e}")

        # 3. זיהוי אוטומטי של משימות ושמירה כ-Pending
        trigger_words = ["תזכיר", "צריך", "לקנות", "משימה", "תקבע", "חשוב ש"]
        if any(word in question.lower() for word in trigger_words):
            await asyncio.to_thread(
                PersistenceManager.append_event, 
                user_id, 
                "task_identified", 
                {"task": question, "source": "chat_input"}, 
                True # מצריך אישור ב-Action Pipeline
            )

        return {"answer_text": response.content}

agent = CoreAgent()