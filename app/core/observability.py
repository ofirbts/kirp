# app/core/observability.py
import time
from collections import deque
from typing import Deque, List


class Observability:
    """
    Lightweight observability helper:
    - tracks query rate (QPS)
    - tracks recent retrieval scores and computes simple drift
    """

    def __init__(self) -> None:
        self.query_timestamps: Deque[float] = deque(maxlen=1000)
        self.last_scores: Deque[float] = deque(maxlen=100)

    def record_query(self) -> None:
        self.query_timestamps.append(time.time())

    def qps(self) -> float:
        now = time.time()
        last_minute: List[float] = [t for t in self.query_timestamps if now - t < 60]
        if not last_minute:
            return 0.0
        return len(last_minute) / 60.0

    def record_score(self, score: float) -> None:
        self.last_scores.append(score)

    def drift(self) -> float:
        if len(self.last_scores) < 10:
            return 0.0
        return float(max(self.last_scores) - min(self.last_scores))
