from app.rag.retriever import retrieve_context
from app.llm.client import get_llm

AGENT_PROMPT = """
You are a proactive personal assistant.

Given the following memories:
{context}

Decide if there is an action you could help with.
If yes – suggest it politely.
If no – answer normally.
"""

async def agent_query(question: str):
    context = retrieve_context(question)
    llm = get_llm()

    response = await llm.apredict(
        AGENT_PROMPT.format(context=context)
    )

    return {
        "answer": response,
        "agent_mode": True
    }

from app.services.trace_logger import log_event

def run_agent(question: str, memories: list, trace_id: str = None):
    if trace_id:
        log_event(trace_id, "agent_started", {"memory_count": len(memories)})
    
    # קוד קיים שלך...
    # (אל תשנה כלום פה)
    
    if trace_id:
        log_event(trace_id, "agent_decision", {
            "answer": answer,
            "suggestions": suggestions
        })
    
    return {
        "answer": answer,
        "sources": memories,
        "suggestions": suggestions,
        "trace_id": trace_id,
        "agent_mode": True
    }

