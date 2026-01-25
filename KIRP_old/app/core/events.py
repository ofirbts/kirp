"""
KIRP Events v7 - Fixed logging
"""
import logging  # Fixed import
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from enum import Enum

from app.core.persistence import PersistenceManager

logger = logging.getLogger(__name__)  # Fixed

class EventType(str, Enum):
    INGEST = "ingest"
    QUERY = "query"

async def emit_ingest_event(text: str, user_id: str, chunks_added: int):
    """Simple event emitter"""
    await PersistenceManager.save_event(
        "ingest", 
        {"text_length": len(text), "chunks_added": chunks_added},
        user_id
    )
