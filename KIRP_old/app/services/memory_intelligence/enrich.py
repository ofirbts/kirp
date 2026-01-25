# app/services/memory_intelligence/enrich.py
from app.models.memory import MemoryRecord
from app.llm.client import llm_call

async def enrich_memory(memory: MemoryRecord) -> dict:
    prompt = f"""
    Analyze the following memory and return:
    - memory_type (MESSAGE / TASK / FACT / IDEA)
    - importance (1-5)
    - tags (list)

    Memory:
    {memory.content}
    """

    return await llm_call(prompt)
