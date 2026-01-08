# app/agent/verifier.py
from typing import Dict, Any


class VerifierAgent:
    def verify(self, answer: str, sources) -> Dict[str, Any]:
        return {
            "verified": bool(sources),
            "source_count": len(sources),
        }
