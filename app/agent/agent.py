import logging
from typing import List, Optional
from app.llm.client import get_llm
from app.rag.vector_store import search_vectors
from app.core.persistence import PersistenceManager
from app.models.schemas import Insight

logger = logging.getLogger(__name__)

class OmniAgent:
    def __init__(self, role: str = "general_assistant"):
        self.role = role
        self.llm = get_llm()

    async def process_task(self, task_description: str, context_query: Optional[str] = None):
        """ביצוע משימה ספציפית (סיכום, זיהוי בעיות וכו')"""
        
        # 1. שליפת הקשר רלוונטי מה-Vector Store אם נדרש
        context = ""
        if context_query:
            results = search_vectors(context_query, k=5)
            context = "\n".join([r['text'] for r in results])

        # 2. בניית ה-Prompt בהתאם לתפקיד (Role)
        system_prompts = {
            "problem_detector": "You are a diagnostic agent. Find anomalies and issues in the data.",
            "auto_summarizer": "You are a summarization agent. Create concise reports from logs.",
            "content_analyzer": "You are a pattern recognition agent. Find trends in user behavior."
        }
        
        full_prompt = f"{system_prompts.get(self.role, '')}\n\nContext:\n{context}\n\nTask: {task_description}"
        
        try:
            # 3. ביצוע הקריאה ל-LLM
            response = await self.llm.ainvoke(full_prompt)
            
            # 4. עדכון הצלחה ב-Persistence (עבור ה-Success Rate ב-UI)
            # כאן היינו מעדכנים מונה הצלחות ב-DB
            
            return response.content
        except Exception as e:
            logger.error(f"❌ Agent Task Error ({self.role}): {e}")
            return f"Task failed: {str(e)}"

# אינסטנס גלובלי לשימוש מהיר
agent = OmniAgent()