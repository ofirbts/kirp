from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import uuid

from app.rag.retriever import retrieve_context
from app.llm.client import get_llm
from app.services.trace_logger import log_event

router = APIRouter(tags=["Agent"])


class AgentRequest(BaseModel):
    question: str


AGENT_PROMPT = """
You are a proactive personal assistant.

Given the following memories:
{context}

Answer the user's question.
If there is a helpful action to suggest, suggest it politely.
"""


@router.post("/")
async def agent_endpoint(request: AgentRequest):
    trace_id = str(uuid.uuid4())[:8]

    try:
        # 1️⃣ שליפת זיכרונות אמיתיים (FAISS + chunks + ranking)
        memories = retrieve_context(request.question)

        log_event(trace_id, "agent_retrieved_memories", {
            "count": len(memories)
        })

        # 2️⃣ בניית prompt
        context_text = "\n\n---\n\n".join(memories)
        llm = get_llm()

        answer = await llm.apredict(
            AGENT_PROMPT.format(context=context_text)
        )

        # 3️⃣ תשובה אמיתית
        return {
            "answer": answer,
            "agent_mode": True,
            "sources": memories,
            "suggestions": [],
            "trace_id": trace_id
        }

    except Exception as e:
        return {
            "answer": f"Agent error: {str(e)}",
            "agent_mode": False,
            "sources": [],
            "suggestions": [],
            "trace_id": trace_id
        }


@router.post("/confirm")
async def confirm_agent(request: dict):
    trace_id = request.get("trace_id", "unknown")
    return {
        "status": "executed",
        "trace_id": trace_id
    }

