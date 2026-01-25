# app/services/pipeline.py
"""
KIRP Unified Ingestion Pipeline v10.1
Enterprise-grade ingestion:
- Intent & memory-type classification (hybrid: heuristics + LLM)
- Chunking (offloaded to thread pool)
- Vector store write (per-user, traceable)
- Events logging (for analytics, dashboard & self-improvement)
"""

import logging
import asyncio
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List

from app.rag.chunker import chunk_text
from app.rag.vector_store import add_texts_with_metadata
from app.core.persistence import PersistenceManager
from app.core.metrics import MetricsCollector
from app.services.intent_classifier_hybrid import HybridIntentClassifier

logger = logging.getLogger(__name__)
metrics = MetricsCollector("ingestion_pipeline")
intent_classifier = HybridIntentClassifier()


class MemoryType(str, Enum):
    TASK = "task"
    EVENT = "event"
    KNOWLEDGE = "knowledge"
    PREFERENCE = "preference"
    LIST = "list"
    CALENDAR = "calendar"
    MEMORY = "memory"  # generic / fallback


def _intent_to_memory_type(intent: str) -> MemoryType:
    """
    Map high-level intent → memory type used for storage/analytics.
    """
    intent = (intent or "memory").lower()

    if intent == "task" or intent == "both":
        return MemoryType.TASK
    if intent == "list":
        return MemoryType.LIST
    if intent == "calendar":
        return MemoryType.CALENDAR

    # ברירת מחדל – ידע כללי / זיכרון
    return MemoryType.KNOWLEDGE


async def _classify_intent(text: str) -> str:
    """
    Use the hybrid classifier (heuristics + LLM) to get a robust intent.
    Always returns a valid string (falls back to 'memory').
    """
    try:
        intent = await intent_classifier.classify(text)
        return intent or "memory"
    except Exception as e:
        logger.error(f"⚠️ Intent classification failed: {e}")
        return "memory"


async def ingest_text(
    text: str,
    source: str = "api",
    metadata: Optional[Dict[str, Any]] = None,
    user_id: str = "system",
) -> Dict[str, Any]:
    """
    Unified ingestion pipeline:

    1. Validation & tracing
    2. Intent classification → memory_type
    3. Chunking (offloaded to thread pool)
    4. Vector store write (per-user)
    5. Event logging for analytics / dashboards / agents

    This function is the **single entrypoint** for:
    - UI ingestion (app/ui/api.py)
    - MemoryStorage.add_memory
    - Imports (app/services/service.py)
    - Future channels (WhatsApp, calendar, etc.)
    """
    if not text or not text.strip():
        raise ValueError("Cannot ingest empty text")

    trace_id = f"tr_{uuid.uuid4().hex[:8]}"
    metrics.inc("ingest_requests")

    logger.info(
        f"🚀 Ingest request | trace={trace_id} | user={user_id} | source={source}"
    )

    # --- 1) Parallel: intent classification + chunking ---
    classify_task = _classify_intent(text)
    chunk_task = asyncio.to_thread(chunk_text, text)

    intent, chunks = await asyncio.gather(classify_task, chunk_task)

    memory_type = _intent_to_memory_type(intent)

    if not chunks:
        logger.warning(
            f"⚠️ No chunks produced | trace={trace_id} | user={user_id} | source={source}"
        )
        await PersistenceManager.append_event(
            "data_ingested_skipped",
            {
                "trace_id": trace_id,
                "reason": "no_chunks",
                "source": source,
                "user_id": user_id,
                "intent": intent,
            },
        )
        metrics.inc("ingest_skipped")
        return {
            "status": "skipped",
            "reason": "no_chunks",
            "trace_id": trace_id,
            "memory_type": memory_type.value,
            "intent": intent,
            "chunks_added": 0,
        }

    # --- 2) Metadata enrichment ---
    enriched_meta = (metadata or {}).copy()
    enriched_meta.update(
        {
            "source": source,
            "memory_type": memory_type.value,
            "intent": intent,
            "trace_id": trace_id,
            "user_id": user_id,
        }
    )

    # --- 3) Vector store write ---
    try:
        chunks_added = add_texts_with_metadata(
            chunks,
            user_id=user_id,
            metadatas=[enriched_meta] * len(chunks),
        )
    except Exception as e:
        logger.error(
            f"❌ Vector store write failed | trace={trace_id} | user={user_id} | error={e}"
        )
        await PersistenceManager.append_event(
            "data_ingested_failed",
            {
                "trace_id": trace_id,
                "source": source,
                "user_id": user_id,
                "intent": intent,
                "memory_type": memory_type.value,
                "error": str(e),
            },
        )
        metrics.inc("ingest_failure")
        return {
            "status": "error",
            "trace_id": trace_id,
            "memory_type": memory_type.value,
            "intent": intent,
            "error": str(e),
            "chunks_added": 0,
        }

    # --- 4) Special handling for tasks / lists / calendar (hooks only, לא שוברים כלום) ---
    try:
        if memory_type == MemoryType.TASK:
            await PersistenceManager.append_event(
                "task_created",
                {
                    "trace_id": trace_id,
                    "user_id": user_id,
                    "source": source,
                    "preview": text[:200],
                },
            )
        elif memory_type == MemoryType.LIST:
            await PersistenceManager.append_event(
                "list_created",
                {
                    "trace_id": trace_id,
                    "user_id": user_id,
                    "source": source,
                    "preview": text[:200],
                },
            )
        elif memory_type == MemoryType.CALENDAR:
            await PersistenceManager.append_event(
                "calendar_intent_detected",
                {
                    "trace_id": trace_id,
                    "user_id": user_id,
                    "source": source,
                    "preview": text[:200],
                },
            )
    except Exception as e:
        # לא מפילים את הצינור בגלל אירוע משני
        logger.warning(f"⚠️ Secondary event hook failed: {e}")

    # --- 5) Main ingestion event ---
    await PersistenceManager.append_event(
        "data_ingested",
        {
            "trace_id": trace_id,
            "memory_type": memory_type.value,
            "intent": intent,
            "source": source,
            "chunk_count": chunks_added,
            "user_id": user_id,
        },
    )

    metrics.inc("ingest_success", chunks_added)
    logger.info(
        f"✅ Ingested {chunks_added} chunks as {memory_type.value} "
        f"(intent={intent}) [trace={trace_id} | user={user_id} | source={source}]"
    )

    return {
        "status": "success",
        "memory_type": memory_type.value,
        "intent": intent,
        "trace_id": trace_id,
        "chunks_added": chunks_added,
    }
