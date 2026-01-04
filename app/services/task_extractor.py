from app.models.memory import MemoryRecord, MemoryType
from app.llm.client import llm_call
from app.storage.memory import save_memory


async def extract_task(memory: MemoryRecord):
    prompt = f"""
    האם יש משימה בטקסט הבא?
    אם כן, החזר רק את המשימה.
    אם לא – החזר NONE.

    טקסט:
    {memory.content}
    """

    result = await llm_call(prompt)

    if result.strip().upper() == "NONE":
        return None

    task = MemoryRecord(
        source="llm_task_extractor",
        content=result,
        memory_type=MemoryType.TASK,
        strength=4
    )

    await save_memory(task)
    return task
