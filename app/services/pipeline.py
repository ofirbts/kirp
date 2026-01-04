# app/services/pipeline.py

import asyncio

from app.rag.chunker import chunk_text
from app.rag.vector_store import add_texts
from app.rag.qa_engine import ask_question

from app.storage.jobs import update_job_status
from app.models.job import JobStatus


# =========================
# Regular ingestion (used by API jobs)
# =========================

async def process_ingest_job(job_id: str, payload: dict):
    try:
        await update_job_status(job_id, JobStatus.IN_PROGRESS)

        text = payload["content"]
        chunks = chunk_text(text)
        add_texts(chunks)

        await asyncio.sleep(0.2)

        await update_job_status(job_id, JobStatus.COMPLETED)

    except Exception:
        await update_job_status(job_id, JobStatus.FAILED)
        raise


# =========================
# Agent-facing API
# =========================

async def ingest_text(text: str) -> None:
    chunks = chunk_text(text)
    add_texts(chunks)


async def answer_question(question: str) -> str:
    return ask_question(question)
