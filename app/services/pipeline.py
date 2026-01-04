import asyncio
from app.models.memory import MemoryRecord, MemoryType
from app.rag.chunker import chunk_text
from app.rag.vector_store import add_texts
from app.rag.qa_engine import ask_question

from app.storage.jobs import update_job_status
from app.models.job import JobStatus


# =========================
# Core Memory Ingest
# =========================

async def ingest_memory(memory: MemoryRecord) -> None:
    """
    Core ingestion logic for ALL memory sources.
    """
    chunks = chunk_text(memory.content)
    add_texts(chunks)


# =========================
# API / Job ingestion
# =========================

async def process_ingest_job(job_id: str, payload: dict):
    try:
        await update_job_status(job_id, JobStatus.IN_PROGRESS)

        memory = MemoryRecord(
            content=payload["content"],
            source=payload.get("source", "api"),
            memory_type=MemoryType.MESSAGE,
        )

        await ingest_memory(memory)

        await asyncio.sleep(0.1)
        await update_job_status(job_id, JobStatus.COMPLETED)

    except Exception:
        await update_job_status(job_id, JobStatus.FAILED)
        raise


# =========================
# Agent-facing API
# =========================

async def ingest_text(text: str) -> None:
    memory = MemoryRecord(
        content=text,
        source="agent",
        memory_type=MemoryType.MESSAGE,
    )
    await ingest_memory(memory)


async def answer_question(question: str) -> str:
    return ask_question(question)
