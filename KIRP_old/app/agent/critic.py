# app/agent/critic.py
from typing import Dict, Any


class CriticAgent:
    def critique(self, answer: str) -> Dict[str, Any]:
        issues = []
        if len(answer) < 20:
            issues.append("Answer too short")

        return {
            "issues": issues,
            "quality": "low" if issues else "ok",
        }
