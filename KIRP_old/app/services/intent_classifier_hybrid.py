# app/services/intent_classifier_hybrid.py
"""
Hybrid Intent Classifier v10
Combines:
- Heuristics (fast, deterministic)
- Keyword intelligence
- LLM fallback (high accuracy)
- Confidence scoring

Returns one of:
- task
- list
- calendar
- event
- knowledge
- memory
"""

import re
import logging
from typing import Optional, Dict, Any

from app.services.intent_classifier_llm import classify_intent_llm

logger = logging.getLogger(__name__)


class HybridIntentClassifier:
    """
    Production-ready hybrid classifier.
    """

    # Keyword maps
    TASK_KEYWORDS = [
        "remind", "todo", "task", "deadline", "finish", "complete",
        "remember to", "i need to", "i must", "i should", "don't forget",
    ]

    LIST_KEYWORDS = [
        "list", "shopping", "groceries", "checklist", "items", "bullets",
        "things to buy", "things to pack",
    ]

    CALENDAR_KEYWORDS = [
        "meeting", "schedule", "appointment", "event", "at", "on",
        "tomorrow", "next week", "at 5pm", "at 10", "friday", "sunday",
    ]

    EVENT_KEYWORDS = [
        "i went", "i saw", "i met", "i visited", "today i", "yesterday i",
        "happened", "occurred",
    ]

    KNOWLEDGE_KEYWORDS = [
        "is", "what is", "how does", "explain", "define", "meaning of",
    ]

    def _match_keywords(self, text: str, keywords: list) -> bool:
        text = text.lower()
        return any(kw in text for kw in keywords)

    def _heuristic_classify(self, text: str) -> Optional[str]:
        """
        Fast deterministic classification.
        Returns None if inconclusive.
        """

        t = text.lower().strip()

        # LIST
        if self._match_keywords(t, self.LIST_KEYWORDS):
            return "list"

        # TASK
        if self._match_keywords(t, self.TASK_KEYWORDS):
            return "task"

        # CALENDAR
        if self._match_keywords(t, self.CALENDAR_KEYWORDS):
            return "calendar"

        # EVENT
        if self._match_keywords(t, self.EVENT_KEYWORDS):
            return "event"

        # KNOWLEDGE
        if self._match_keywords(t, self.KNOWLEDGE_KEYWORDS):
            return "knowledge"

        # If text looks like a list
        if "\n" in t and len(t.split("\n")) >= 3:
            return "list"

        # If text contains a date/time pattern
        if re.search(r"\b\d{1,2}(:\d{2})?\s?(am|pm)?\b", t):
            return "calendar"

        return None  # inconclusive

    async def classify(self, text: str) -> str:
        """
        Hybrid classification:
        1. Heuristics (fast)
        2. LLM fallback (accurate)
        """

        # 1. Heuristic pass
        heuristic = self._heuristic_classify(text)
        if heuristic:
            logger.info(f"🧠 Heuristic intent: {heuristic}")
            return heuristic

        # 2. LLM fallback
        try:
            llm_intent = await classify_intent_llm(text)
            if llm_intent:
                logger.info(f"🤖 LLM intent: {llm_intent}")
                return llm_intent
        except Exception as e:
            logger.error(f"LLM intent classification failed: {e}")

        # 3. Fallback
        return "memory"
