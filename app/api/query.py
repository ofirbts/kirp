from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.agent.agent import agent  # שימוש בסינגלטון
from app.api.status import mark_query, mark_error

router = APIRouter(tags=["Query"])

class QueryRequest(BaseModel):
    query: str
    session_id: str = "default"
    k: int = 5

@router.post("")
async def query_endpoint(req: QueryRequest):
    try:
        result = await agent.query(req.query)

        mark_query()
        return result

    except Exception as e:
        mark_error(f"query_failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(e)}"
        )

