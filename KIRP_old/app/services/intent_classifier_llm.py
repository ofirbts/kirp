# app/services/intent_classifier_llm.py

import json
import logging
from enum import Enum
from app.llm.client import llm_call

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    MEMORY = "memory"
    TASK = "task"
    LIST = "list"
    CALENDAR = "calendar"
    QUERY = "query"
    BOTH = "both"


INTENT_PROMPT = """
You are an intent classifier. 
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
{{
  "intent": "<intent>"
}}
"""


class LLMIntentClassifier:
    async def classify(self, text: str) -> IntentType:
        """
        מחזיר IntentType על בסיס LLM.
        עמיד לשגיאות ולתשובות לא תקינות.
        """

        try:
            raw = await llm_call(INTENT_PROMPT.format(text=text))

            # ניסיון לפענח JSON מתוך תשובת LLM
            try:
                resp = json.loads(raw)
            except Exception:
                logger.warning(f"⚠️ LLM returned non-JSON: {raw}")
                return IntentType.MEMORY

            intent = resp.get("intent", "memory").lower()

            # הגנה: אם המודל מחזיר משהו לא חוקי
            if intent not in IntentType._value2member_map_:
                logger.warning(f"⚠️ Invalid intent from LLM: {intent}")
                return IntentType.MEMORY

            return IntentType(intent)

        except Exception as e:
            logger.error(f"❌ Intent classification failed: {e}")
            return IntentType.MEMORY
