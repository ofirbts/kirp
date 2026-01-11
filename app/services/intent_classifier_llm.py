from enum import Enum
from app.llm.client import llm_complete

class IntentType(str, Enum):
    MEMORY = "memory"
    TASK = "task"
    LIST = "list"
    CALENDAR = "calendar"
    QUERY = "query"
    BOTH = "both"

INTENT_PROMPT = """
Classify the user intent.
Return JSON ONLY.

Possible intents:
- memory
- task
- list
- calendar
- both
- query

User input:
"{text}"

Answer format:
{{ "intent": "<intent>" }}
"""

class LLMIntentClassifier:
    async def classify(self, text: str) -> IntentType:
        resp = await llm_complete(
            INTENT_PROMPT.format(text=text),
            temperature=0
        )
        intent = resp.get("intent", "memory")
        return IntentType(intent)
