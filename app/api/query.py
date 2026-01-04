from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.router import agent_handle

router = APIRouter()


class AgentInput(BaseModel):
    text: str


@router.post("/")
async def query(input: AgentInput):
    return await agent_handle(input.text)
