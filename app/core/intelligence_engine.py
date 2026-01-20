import logging
import json
import uuid
from typing import List
from app.core.persistence import PersistenceManager
from app.llm.client import get_llm
from app.rag.vector_store import search_vectors
from app.models.schemas import Insight

logger = logging.getLogger(__name__)

class IntelligenceEngine:
    @staticmethod
    async def generate_system_insights(user_id: str) -> List[Insight]:
        """ניתוח אירועים ומידע מהוקטורים ליצירת תובנות אסטרטגיות"""
        llm = get_llm()
        
        # 1. שליפת דאטה רלוונטי מהוקטורים (Context-Aware)
        # המנוע בודק מה המערכת למדה לאחרונה
        try:
            recent_data = search_vectors("current system patterns and user feedback", k=15)
            context = "\n".join([f"[{d['metadata'].get('source', 'unknown')}]: {d['text']}" for d in recent_data])
        except Exception as e:
            logger.warning(f"Vector search failed during insight generation: {e}")
            context = "No recent vector data available."

        prompt = f"""
        You are the KIRP Intelligence Engine (OS Kernel Level). 
        Analyze the following organizational data context and generate actionable insights.
        
        Look for:
        1. RISKS: Performance issues, gaps in knowledge, or security concerns.
        2. OPPORTUNITIES: Patterns that can be automated, recurring questions, or process improvements.
        3. TRENDS: Changes in user interest or system behavior.

        Context Data:
        {context}
        
        Return a JSON list of Insight objects ONLY.
        Format: [{{ "title": "...", "description": "...", "type": "risk/opportunity/trend", "confidence": 0.9, "impact_score": 8 }}]
        """
        
        try:
            response = await llm.ainvoke(prompt)
            # ניקוי Markdown JSON כדי למנוע שגיאות פענוח
            content = response.content.strip()
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            raw_insights = json.loads(content)
            
            insights_list = []
            for item in raw_insights:
                insight = Insight(
                    id=str(uuid.uuid4()),
                    status="new",
                    **item
                )
                # שמירה ל-DB דרך המנהל החדש (שמונע כפילויות)
                await PersistenceManager.save_insight(user_id, insight)
                insights_list.append(insight)
                
            return insights_list 
               
        except Exception as e:
            logger.error(f"❌ Intelligence Engine Error: {e}")
            return []

    @staticmethod
    async def analyze_system_logs(logs: List[str]) -> List[Insight]:
        """הופך לוגים טכניים לתובנות עסקיות ותפעוליות"""
        llm = get_llm()
        
        prompt = f"""
        Analyze these KIRP OS logs. Identify critical bottlenecks or recurring failures.
        Logs: {logs[-20:]}
        Return a JSON list of insights with 'title', 'description', and 'type'.
        """
        
        try:
            response = await llm.ainvoke(prompt)
            content = response.content.replace("```json", "").replace("```", "").strip()
            raw_insights = json.loads(content)
            return [Insight(id=str(uuid.uuid4()), confidence=0.95, status="new", **item) for item in raw_insights]
        except Exception as e:
            logger.error(f"Log Analysis Failed: {e}")
            return []

    @staticmethod
    async def propose_self_improvement(health_data: dict):
        """מנוע שיפור עצמי - סעיף 7 באפיון"""
        llm = get_llm()
        prompt = f"""
        System Health Report: {health_data}
        As the system architect, suggest one specific technical optimization to improve latency or reliability.
        Provide a concise technical recommendation.
        """
        return await llm.ainvoke(prompt)
    
    @staticmethod
    async def process_job(job: dict):
        """עיבוד עבודות אינג'סטציה - הפיכת דאטה גולמי לוקטורים"""
        logger.info(f"⚙️ Processing job {job['id']} for source {job['source']}")
        # כאן תבוא לוגיקה של Chunking ו-Embedding
        # לבינתיים, אנחנו מעדכנים סטטוס ל-DONE כדי שה-UI יתעדכן
        db = await PersistenceManager.get_db()
        await db.jobs.update_one({"id": job['id']}, {"$set": {"status": "DONE"}})

    @staticmethod
    async def analyze_trends(events: List[dict]) -> List[Insight]:
        """מנתח אירועים אחרונים ומייצר מהם תובנות ללא צורך בוקטורים"""
        llm = get_llm()
        event_summary = "\n".join([f"- {e['event_type']}: {e['payload']}" for e in events])
        
        prompt = f"""Analyze these recent system events and create 2-3 strategic insights:
        {event_summary}
        Return JSON list of Insight objects."""
        
        # ... לוגיקת ה-LLM הקיימת שלך ...
        return await IntelligenceEngine.generate_system_insights("system_user")