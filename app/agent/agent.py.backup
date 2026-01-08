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
