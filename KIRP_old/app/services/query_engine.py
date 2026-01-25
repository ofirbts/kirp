import logging
from app.agent.agent import agent
from app.core.persistence import PersistenceManager

logger = logging.getLogger(__name__)

async def execute_query(question: str, user_id: str = "default"):
    try:
        response = await agent.process_task(
            task_description=question, 
            user_id=user_id,
            context_query=question
        )
        return response
    except Exception as e:
        logger.error(f"Query Engine Error: {e}")
        return f"מצטער, חלה שגיאה בעיבוד השאילתה: {str(e)}"
