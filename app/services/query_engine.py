from app.services.intent_classifier_llm import LLMIntentClassifier
from app.services.task_extractor import TaskExtractor
from app.services.memory import MemoryService
from app.services.task_service import TaskService
from app.services.list_service import ListService
from app.services.calendar_service import CalendarService
from app.rag.qa_engine import answer_with_rag

classifier = LLMIntentClassifier()

async def intelligent_query(user_input: str) -> dict:
    intent = await classifier.classify(user_input)

    effects = {
        "memory": False,
        "tasks": [],
        "lists": [],
        "calendar": []
    }

    if intent in ("memory", "both"):
        MemoryService.store(user_input)
        effects["memory"] = True

    if intent in ("task", "both"):
        tasks = TaskExtractor.extract(user_input)
        for t in tasks:
            TaskService.create(t)
            effects["tasks"].append(t)

    if intent == "list":
        effects["lists"] = ListService.extract_and_create(user_input)

    if intent == "calendar":
        effects["calendar"] = CalendarService.extract_and_create(user_input)

    answer = await answer_with_rag(user_input)

    return {
        "intent": intent,
        "effects": effects,
        "answer": answer
    }
