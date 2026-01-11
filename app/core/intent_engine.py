from typing import Dict
import re

class IntentEngine:
    """
    Deterministic intent classifier for KIRP.
    Supports Hebrew + English, memory commands, ignore commands,
    and tier selection (short/long).
    """

    STORE_PATTERNS = [
        r"remember",
        r"save this",
        r"store this",
        r"תזכור",
        r"תזכיר לי",
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
        lowered = text.strip().lower()

        # Ignore
        for p in self.IGNORE_PATTERNS:
            if re.search(p, lowered):
                return {"intent": "ignore"}

        # Store memory
        for p in self.STORE_PATTERNS:
            if re.search(p, lowered):
                tier = "long" if "נקרא" in lowered else "short"
                return {"intent": "store_memory", "tier": tier}

        # Default
        return {"intent": "answer_only"}
