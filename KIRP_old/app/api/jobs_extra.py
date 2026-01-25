# app/api/jobs_extra.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from app.core.persistence import PersistenceManager

router = APIRouter(prefix="/jobs", tags=["jobs-extra"])


class JobsSummary(BaseModel):
    total: int
    done: int
    failed: int
    in_progress: int


@router.get("/summary", response_model=JobsSummary)
async def jobs_summary():
    db = await PersistenceManager.get_db()
    total = await db.jobs.count_documents({})
    done = await db.jobs.count_documents({"status": "DONE"})
    failed = await db.jobs.count_documents({"status": "FAILED"})
    in_progress = total - done - failed
    return JobsSummary(
        total=total,
        done=done,
        failed=failed,
        in_progress=in_progress,
    )


@router.post("/{job_id}/retry")
async def retry_job(job_id: str):
    """
    מסמן Job כ-Retry ומנקה שגיאה, כדי שה-Worker יוכל להריץ אותו שוב.
    """
    db = await PersistenceManager.get_db()
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    await db.jobs.update_one(
        {"id": job_id},
        {"$set": {"status": "RETRY", "error_message": None}},
    )

    # רישום אירוע כללי (לא חובה, אבל יפה ל-Observability)
    await PersistenceManager.save_event("job_retry", {"job_id": job_id})

    return {"status": "retry_scheduled", "job_id": job_id}


@router.get("/{job_id}/explain")
async def explain_job(job_id: str) -> Dict[str, Any]:
    """
    מחזיר הסבר טכני על ה-Job – לשימוש ב-UI.
    """
    db = await PersistenceManager.get_db()
    job = await db.jobs.find_one({"id": job_id})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "source": job.get("source"),
        "status": job.get("status"),
        "chunks_count": job.get("chunks_count"),
        "processing_time_ms": job.get("processing_time_ms"),
        "reason": job.get("error_message", "No error recorded."),
        "pipeline_stages": [
            "RECEIVED",
            "CHUNKED",
            "EMBEDDED",
            "STORED",
            "DONE",
        ],
    }
