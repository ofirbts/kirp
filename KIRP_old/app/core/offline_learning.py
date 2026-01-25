from collections import defaultdict
from typing import Dict, Any, List


class OfflineLearner:
    def analyze(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        stats = defaultdict(int)
        confidences = []

        for e in events:
            # Count decisions
            if e["type"] in ("agent_async_decision", "agent_decision"):
                stats["decisions"] += 1

            # Extract confidence from agent_decision
            if e["type"] == "agent_decision":
                c = e["payload"].get("confidence")
                if isinstance(c, (int, float)):
                    confidences.append(c)

            # Extract confidence from explanation (if exists)
            if e["type"] == "explanation":
                c = e["payload"].get("confidence")
                if isinstance(c, (int, float)):
                    confidences.append(c)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        return {
            "total_decisions": stats["decisions"],
            "avg_confidence": round(avg_conf, 3),
            "confidence_samples": len(confidences),
        }
