from typing import Literal
from app.llm.client import get_llm

MemoryType = Literal["task", "knowledge", "event", "note"]

CLASSIFY_PROMPT = """
Classify the following text into ONE memory type:

- task: actionable, requires execution
- knowledge: information to remember
- event: time-bound event
- note: reflection or idea

Text:
{input}

Return only one word.
"""

async def classify_memory(text: str) -> MemoryType:
    llm = get_llm()
    result = await llm.apredict(CLASSIFY_PROMPT.format(input=text))
    return result.strip().lower()
