from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.agent import agent

router = APIRouter(tags=["Agent"])

class QueryRequest(BaseModel):
    query: str
    user_id: str = "ofir"

@router.post("")
async def query_endpoint(req: QueryRequest):
    try:
        # שליחה ל-Agent עם user_id כפי שהוא מצפה
        return await agent.query(req.query, user_id=req.user_id)
    except Exception as e:
        import logging
        logging.error(f"Error in query_endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))