import logging
from typing import List
from app.llm.client import get_llm
from app.rag.vector_store import search_vectors
from app.models.schemas import Insight
import json
import uuid

logger = logging.getLogger(__name__)

class IntelligenceEngine:
    @staticmethod
    async def generate_system_insights(user_id: str) -> List[Insight]:
        """סריקת מאגר הידע ויצירת תובנות אוטונומיות"""
        llm = get_llm()
        
        # 1. שליפת פריטי ידע אחרונים כקונטקסט (דוגמה ל-50 פריטים)
        recent_data = search_vectors("latest updates and common issues", k=10)
        context = "\n".join([d['text'] for d in recent_data])
        
        prompt = f"""
        Analyze the following knowledge data and identify 3 key business insights.
        Categorize each as 'trend', 'opportunity', or 'risk'.
        Provide a confidence score (0-1) and an impact score (1-10).
        
        Data:
        {context}
        
        Return ONLY a JSON list of objects with: title, description, type, confidence, impact_score.
        """
        
        try:
            # שימוש ב-invoke (תואם לגרסאות LangChain החדשות שהעלית)
            response = await llm.ainvoke(prompt)
            raw_insights = json.loads(response.content)
            
            insights = []
            for item in raw_insights:
                insights.append(Insight(
                    id=str(uuid.uuid4()),
                    **item
                ))
            return insights
        except Exception as e:
            logger.error(f"❌ Insight Generation Error: {e}")
            return []

    @staticmethod
    async def propose_self_improvement(current_config: dict):
        """סעיף 7 באפיון: מנוע שיפור עצמי שמציע עדכוני מערכת"""
        llm = get_llm()
        # כאן בעתיד נשלב סריקה של בלוגים חיצוניים (LangChain/Pinecone)
        prompt = f"Based on current config {current_config}, suggest one technical improvement for the RAG pipeline."
        return await llm.ainvoke(prompt)
    
    @staticmethod
    async def analyze_system_logs(logs: List[str]) -> List[Insight]:
        """ניתוח לוגים גולמיים והפיכתם לתובנות תפעוליות"""
        llm = get_llm()
        
        prompt = f"""
        Analyze these system logs from KIRP OS. 
        Identify performance bottlenecks, database issues, or security warnings.
        
        Logs:
        {logs[-20:]} # ניתוח 20 השורות האחרונות
        
        Return a JSON list of Insights with title, description, and type ('risk' or 'opportunity').
        """
        
        try:
            response = await llm.ainvoke(prompt)
            # לוגיקה לעיבוד ה-JSON ושמירה ב-DB דרך PersistenceManager
            return response.content
        except Exception as e:
            logger.error(f"Log Analysis Failed: {e}")
            return []