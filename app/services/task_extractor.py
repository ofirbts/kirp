from app.models.memory import MemoryRecord, MemoryType
from app.models.task import Task
from app.llm.client import llm_call
from app.storage.memory import save_memory
from app.storage.tasks import create_task

KEYWORDS = ["צריך", "לעשות", "לא לשכוח", "תזכורת"]

async def extract_task(memory: MemoryRecord):
    # בדיקה מהירה עם מילות מפתח
    if any(word in memory.content for word in KEYWORDS):
        # שימוש ב-LLM לחילוץ מדויק
        prompt = f"""
        האם יש משימה בטקסט הבא?
        אם כן, החזר רק את המשימה המדויקת (עד 100 תווים).
        אם לא – החזר NONE.

        טקסט: {memory.content}
        """
        
        result = await llm_call(prompt)
        
        if result.strip().upper() != "NONE":
            # יצירת MemoryRecord של משימה
            task_memory = MemoryRecord(
                source="llm_task_extractor",
                content=result.strip()[:100],
                memory_type=MemoryType.TASK,
                strength=4,
                parent_id=memory.id  # קישור לזיכרון המקורי
            )
            await save_memory(task_memory)
            
            # יצירת Task במקביל
            task = Task(
                title=result.strip()[:80],
                source_memory_id=memory.id
            )
            await create_task(task)
            
            return task_memory
    
    return None
