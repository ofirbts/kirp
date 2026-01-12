import re
from typing import Dict

class IntentEngine:
    """
    Deterministic intent classification.
    """

    STORE_PATTERNS = [
        r"remember",
        r"save this",
        r"store this",
        r"תזכור",
        r"תשמור",
        r"אל תשכח",
    ]

    IGNORE_PATTERNS = [
        r"ignore",
        r"forget",
        r"תשכח",
        r"\bok\b",
        r"thanks",
        r"👍",
    ]

    def classify(self, text: str) -> Dict[str, str]:
        lowered = text.lower().strip()

        for p in self.IGNORE_PATTERNS:
            if re.search(p, lowered):
                return {"intent": "ignore"}

        for p in self.STORE_PATTERNS:
            if re.search(p, lowered):
                tier = "long" if "נקרא" in lowered else "short"
                return {"intent": "store_memory", "tier": tier}

        return {"intent": "answer_only"}
