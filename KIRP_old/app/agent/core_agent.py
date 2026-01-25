import asyncio
import logging
from app.core.persistence import PersistenceManager
from app.services.notion.notion_impl import NotionClient

logger = logging.getLogger(__name__)
notion = NotionClient()

class CoreAgent:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info("🚀 CoreAgent System Started")
        while self.running:
            await self.process_pending_events()
            await asyncio.sleep(10)

    async def process_pending_events(self):
        try:
            pending = await PersistenceManager.get_pending_improvements()
            for event in pending:
                if not event.get("applied"):
                    loop = asyncio.get_running_loop()
                    # הרצה ב-executor כדי לא לחסום את הצ'אט בזמן פנייה ל-Notion
                    success = await loop.run_in_executor(None, self.attempt_apply_improvement, event)
                    if success:
                        await PersistenceManager.apply_config_change(event.get("_id"))
        except Exception as e:
            logger.error(f"Error in CoreAgent events: {e}")

    def attempt_apply_improvement(self, improvement):
        try:
            return bool(notion.create_task(
                title=f"Improvement {improvement.get('_id')}",
                trace_id=str(improvement.get('_id')),
                source="KIRP Improvement Engine"
            ))
        except:
            return False

class ScraperAgent:
    async def scrape_and_append_event(self, task_data: dict):
        return await PersistenceManager.append_event("task_identified", task_data)

class KafkaEventAgent:
    async def consume_event(self, message: dict):
        return await PersistenceManager.append_event(message.get("type", "unknown"), message.get("payload", {}))

agent = CoreAgent()
