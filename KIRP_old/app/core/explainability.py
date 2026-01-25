# app/core/explanation_builder.py
from typing import Dict, Any, List
from datetime import datetime, timezone


class ExplanationBuilder:
    """
    Lightweight explainability helper.

    Produces structured records explaining:
    - Why the agent made a decision
    - What inputs were used
    - What outcome was produced
    """

    def explain(self, reason: str, inputs: Dict[str, Any], outcome: Any) -> Dict[str, Any]:
        """
        Build a single explanation record.
        """
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reason": reason,
            "inputs": inputs,
            "outcome": outcome,
        }

    def summarize(self, explanations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize a list of explanation records.
        Useful for audits, debugging, and transparency.
        """
        summary: Dict[str, Any] = {
            "total_explanations": len(explanations),
            "common_reasons": {},
        }

        for exp in explanations:
            reason = exp.get("reason", "unknown")
            summary["common_reasons"][reason] = (
                summary["common_reasons"].get(reason, 0) + 1
            )

        return summary
