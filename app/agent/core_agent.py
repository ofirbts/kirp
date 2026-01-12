# app/agent/core_agent.py (הגרסה המאוחדת והמשופרת)
import asyncio
import logging
from typing import Dict, Any
from app.core.persistence import PersistenceManager
from app.core.metrics import metrics
from app.services.notion import notion # חיבור ישיר ל-Notion

logger = logging.getLogger(__name__)

class CoreAgent:
    def __init__(self):
        self.running = False

    async def start(self):
        self.running = True
        logger.info("🚀 CoreAgent System Started")
        while self.running:
            await self.process_pending_events()
            await asyncio.sleep(5)

    async def process_pending_events(self):
        pending = PersistenceManager.get_pending_approvals()
        for event in pending:
            # כאן המערכת עוברת על אירועים שמחכים לאישור
            # אם אישרת ב-UI, הסטטוס ישתנה וזה יצא מהלופ
            logger.info(f"Checking status for event {event['id']}: {event['status']}")

# סוכנים ייעודיים (יכולים להישאר בקבצים נפרדים או כאן)
class ScraperAgent:
    def scrape_and_append_event(self, task_data: dict):
        # הוספת הרישום למטריקות ודיווח ל-Persistence
        event_id = PersistenceManager.append_event("task_identified", task_data, requires_approval=True)
        metrics.record_query()
        return event_id

class KafkaEventAgent:
    def consume_event(self, message: dict):
        event_id = PersistenceManager.append_event(
            message.get("type", "unknown"), 
            message.get("payload", {}), 
            requires_approval=True
        )
        metrics.record_query()
        return event_id