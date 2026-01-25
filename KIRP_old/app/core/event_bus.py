# app/core/event_bus.py
import json
import logging
from typing import Dict, Any

from app.core.redis_client import get_redis

logger = logging.getLogger("EventBus")

EVENT_QUEUE = "kirp_events"


def publish_event(event_type: str, data: Dict[str, Any]) -> None:
    """
    דוחף אירוע ל-Redis Queue בצורה סטנדרטית.
    """
    redis = get_redis()
    payload = {
        "type": event_type,
        "data": data,
    }
    redis.rpush(EVENT_QUEUE, json.dumps(payload))
    logger.info(f"📨 Event published: type={event_type}")
