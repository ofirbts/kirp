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
        # 1. שליפת אירועים
        raw_events = await asyncio.to_thread(PersistenceManager.get_all_events, limit=50)
        
        processed_context_parts = []
        now = datetime.utcnow()

        for e in raw_events:
            # חישוב דעיכה (Decay)
            importance = e.get("importance", 1)
            try:
                timestamp = datetime.fromisoformat(e["timestamp"])
            except:
                timestamp = now
                
            days_passed = (now - timestamp).days
            effective_score = importance - (days_passed * 0.1)
            
            # בניית משפט הקשר רק אם המידע עדיין רלוונטי
            if effective_score > 0:
                e_type = e.get('type', '')
                data = e.get('data', {})
                
                if e_type == 'knowledge_add':
                    content = data.get('text', '')
                    processed_context_parts.append(f"[מידע - חשיבות {effective_score:.1f}]: {content}")
                elif e_type == 'task_identified':
                    task = data.get('task', '')
                    processed_context_parts.append(f"[משימה - חשיבות {effective_score:.1f}]: {task}")

        context_str = "\n".join(processed_context_parts)

        # 2. ה-Prompt המשודרג (הזהות של אופיר)
        refine_prompt = f"""
        אתה KIRP OS, ה-AI האישי של אופיר בטש. 
        אופיר הוא מנהל פרויקטים מנוסה (10+ שנים) עם לב ענק, איש של אמונה וערכים שעושה מעבר לעולם הטכנולוגי.
        
        הקשר נוכחי מהזיכרון (מסודר לפי חשיבות ורלוונטיות):
        {context_str}
        
        הנחיות לתשובה חכמה:
        1. חבר נקודות: תבין את הקשר בין המשימות הטכניות (Docker, RAG) לבין המטרות האישיות של אופיר.
        2. תעדוף חכם: אם יש הרבה משימות, תדגיש את אלו עם ה-Score הגבוה ביותר.
        3. שפה: עברית רהוטה, חמה, מקצועית ומעודדת.
        
        שאלה: {question}
        """

        response = await self.llm.ainvoke([("system", refine_prompt), ("user", question)])
        
        # זיהוי משימה ושמירה (המנגנון החכם ב-PersistenceManager כבר יטפל בכפילויות)
        if any(word in question.lower() for word in ["תזכיר", "צריך", "לקנות", "משימה"]):
            await asyncio.to_thread(PersistenceManager.append_event, "task_identified", {"task": question}, True)

        return {"answer_text": response.content}
    
agent = CoreAgent()
