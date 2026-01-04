from enum import Enum
from typing import Literal

from app.services.pipeline import ingest_text, answer_question


class InputType(str, Enum):
    MESSAGE = "message"
    QUESTION = "question"


def classify_input(text: str) -> InputType:
    """
    Heuristic simple classifier.
    Later can be replaced with LLM-based routing.
    """
    if "?" in text or text.strip().startswith(("מה", "איך", "למה")):
        return InputType.QUESTION
    return InputType.MESSAGE


async def agent_handle(text: str) -> dict:
    intent = classify_input(text)

    if intent == InputType.MESSAGE:
        await ingest_text(text)
        return {
            "action": "ingest",
            "message": "Information stored successfully"
        }

    if intent == InputType.QUESTION:
        answer = await answer_question(text)
        return {
            "action": "query",
            "answer": answer
        }

    return {"error": "Unknown intent"}
