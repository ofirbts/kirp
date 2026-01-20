import logging
from datetime import datetime, timezone
from typing import Any, Dict
from app.models.events import KIRPEvent
from app.core.persistence import PersistenceManager

logger = logging.getLogger(__name__)

class EventBus:
    @staticmethod
    async def emit(event_type: str, source: str, payload: Dict[str, Any], trace_id: str = None):
        event = KIRPEvent(
            trace_id=trace_id or f"tr_{datetime.now(timezone.utc).timestamp()}",
            event_type=event_type,
            source=source,
            payload=payload
        )
        
        # 1. שמירה ל-Permanent Record (ה-Memory של ה-OS)
        db = await PersistenceManager.get_db()
        await db.events.insert_one(event.dict())
        
        # 2. לוג מערכתי
        logger.info(f" [EVENT] {event.event_type} from {event.source} | Trace: {event.trace_id}")
        
        # 3. כאן נכנס ה-Loop: האם יש סוכן שצריך להגיב לאירוע הזה?
        # בעתיד: if event_type == "data_ingested": trigger_insight_scan()
        return event