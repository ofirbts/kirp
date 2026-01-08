import time
from collections import deque
from typing import Deque, List, Dict


class Observability:
    def __init__(self) -> None:
        self.query_timestamps: Deque[float] = deque(maxlen=2000)
        self.last_scores: Deque[float] = deque(maxlen=200)
        self.alerts: List[Dict[str, str]] = []

    def record_query(self) -> None:
        self.query_timestamps.append(time.time())

    def qps(self) -> float:
        now = time.time()
        recent = [t for t in self.query_timestamps if now - t < 60]
        return len(recent) / 60.0 if recent else 0.0

    def record_score(self, score: float) -> None:
        self.last_scores.append(score)

    def drift(self) -> float:
        if len(self.last_scores) < 20:
            return 0.0
        return float(max(self.last_scores) - min(self.last_scores))

    def check_alerts(self) -> List[Dict[str, str]]:
        self.alerts.clear()

        if self.qps() > 5.0:
            self.alerts.append({
                "type": "high_qps",
                "message": "Query rate unusually high",
            })

        if self.drift() > 0.5:
            self.alerts.append({
                "type": "embedding_drift",
                "message": "High retrieval score drift detected",
            })

        return self.alerts
