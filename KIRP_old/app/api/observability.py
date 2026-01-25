from fastapi import APIRouter
from app.observability.metrics import get_metrics

router = APIRouter()

@router.get("/metrics")
def metrics():
    return get_metrics()
