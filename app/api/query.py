from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Query"])  # ❌ הסר prefix="/query"

class QueryRequest(BaseModel):
    question: str

@router.post("/")
async def query_endpoint(request: QueryRequest):
    return {"answer": f"KIRP: {request.question}"}
