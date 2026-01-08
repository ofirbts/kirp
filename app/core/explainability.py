from typing import Dict, Any, List
from datetime import datetime


class ExplanationBuilder:
    """
    Very lightweight explainability helper.

    It does NOT try to re-implement the full retrieval_pipeline explanation,
    but gives a structured, stable schema for "why the agent did X".
    """

    def explain(self, reason: str, inputs: Dict[str, Any], outcome: Any) -> Dict[str, Any]:
        """
        Build a single explanation record.

        This is what is persisted into events as "explanation".
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "inputs": inputs,
            "outcome": outcome,
        }

    def summarize(self, explanations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize a list of explanation records.

        This is intentionally simple – the goal is to have something
        cheap but useful that can be used in audits / debug.
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
