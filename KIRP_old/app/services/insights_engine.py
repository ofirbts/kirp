import logging
from datetime import datetime, timezone
from app.core.persistence import PersistenceManager
from app.rag.rag_engine import rag_engine

logger = logging.getLogger("InsightsEngine")


class InsightsEngine:
    @staticmethod
    async def generate_user_insights(user_id: str):
        """מנתח את הודעות המשתמש האחרונות ומפיק תובנות אסטרטגיות"""
        db = await PersistenceManager.get_db()

        recent_knowledge = await db.knowledge.find(
            {"user_id": user_id}
        ).sort("created_at", -1).to_list(20)

        if not recent_knowledge:
            return

        full_text = "\n".join([k["text"] for k in recent_knowledge])

        prompt = f"""
Analyze the following recent inputs from user '{user_id}' and identify:
1. Patterns or recurring themes.
2. Potential risks or 'dead ends'.
3. Strategic opportunities.

Inputs:
{full_text}

Return the result in a concise, structured way.
"""

        result = await rag_engine.query(prompt, user_id=user_id)
        analysis = result.get("answer", "")

        insight_doc = {
            "user_id": user_id,
            "title": f"Summary for {datetime.now().strftime('%Y-%m-%d')}",
            "description": analysis,
            "type": "trend",
            "status": "new",
            "confidence": 0.85,
            "created_at": datetime.now(timezone.utc),
        }
        await db.insights.insert_one(insight_doc)
        logger.info(f"✅ Generated new insight for {user_id}")
