from fastapi import APIRouter, BackgroundTasks
from app.models.ingest import IngestRequest
from app.storage.jobs import create_job
from app.services.pipeline import process_ingest_job

router = APIRouter()

@router.post("/")
async def ingest(data: IngestRequest, background_tasks: BackgroundTasks):
    job_payload = data.dict()

    job_id = await create_job({
        "type": "INGEST_MESSAGE",
        "status": "PENDING",
        "payload": job_payload
    })

    background_tasks.add_task(process_ingest_job, job_id, job_payload)

    return {
        "status": "accepted",
        "job_id": job_id
    }
