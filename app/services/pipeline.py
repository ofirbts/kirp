from app.models.memory import MemoryRecord
from app.services.memory_classifier import classify_memory
from app.storage.memory import save_memory
from app.rag.chunker import chunk_text
from app.rag.vector_store import add_texts
import asyncio
from app.models.job import JobStatus
from app.storage.jobs import update_job_status
from app.services.task_extractor import extract_task
from app.rag.qa_engine import answer_with_rag  # ✅ החלפה נכונה

# =========================
# Core memory ingestion
# =========================

async def ingest_memory(memory: MemoryRecord) -> None:
    """
    Single source of truth for memory ingestion.
    """
    record = MemoryRecord(
        source=memory.source,
        content=memory.content,
        memory_type=memory.memory_type
    )
    await save_memory(record)
    await extract_task(record)

    chunks = chunk_text(memory.content)
    add_texts(chunks)

# =========================
# Public API / Agent entry
# =========================

async def ingest_text(text: str, source: str = "agent") -> None:
    memory_type = classify_memory(text)

    memory = MemoryRecord(
        source=source,
        content=text,
        memory_type=memory_type
    )

    await ingest_memory(memory)

# =========================
# Question answering
# =========================

async def answer_question(question: str) -> str:
    return await answer_with_rag(question)  # ✅ החלפה ל-RAG חדש

# =========================
# Job-based ingestion
# =========================

async def process_ingest_job(job_id: str, payload: dict):
    try:
        await update_job_status(job_id, JobStatus.IN_PROGRESS)

        memory_type = payload.get("memory_type")
        if memory_type is None:
            memory_type = classify_memory(payload["content"])

        memory = MemoryRecord(
            content=payload["content"],
            source=payload.get("source", "api"),
            memory_type=memory_type
        )

        await ingest_memory(memory)

        await asyncio.sleep(0.1)
        await update_job_status(job_id, JobStatus.COMPLETED)

    except Exception:
        await update_job_status(job_id, JobStatus.FAILED)
        raise
