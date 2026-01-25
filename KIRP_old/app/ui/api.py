# app/ui/api.py
import asyncio
import logging
from app.agent.agent import agent
from app.services.pipeline import ingest_text


logger = logging.getLogger(__name__)

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

def ingest(text: str, user_id: str):
    """
    Ingest מה־UI עם שיוך למשתמש האמיתי.
    """
    return run_async(
        ingest_text(
            text,
            source="ui_manual",
            metadata={"user_id": user_id},
        )
    )

def ask(question: str, user_id: str):
    """
    שאלה לצ'אט עם שיוך user_id אמיתי.
    """
    return run_async(
        agent.process_task(
            task_description=question,
            user_id=user_id,
            context_query=question,
        )
    )

