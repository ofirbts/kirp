from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.agent import agent

router = APIRouter(tags=["Agent"])

class QueryRequest(BaseModel):
    query: str

@router.post("")
async def query_endpoint(req: QueryRequest):
    try:
        return await agent.query(req.query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
