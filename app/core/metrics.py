from collections import defaultdict
from datetime import datetime

class Metrics:
    def __init__(self):
        self.counters = defaultdict(int)
        self.timings = []
        self.last_updated = None

    def inc(self, name: str):
        self.counters[name] += 1
        self.last_updated = datetime.utcnow().isoformat()

    def timing(self, name: str, ms: float):
        self.timings.append({
            "metric": name,
            "ms": ms,
            "ts": datetime.utcnow().isoformat()
        })

    def snapshot(self):
        return {
            "counters": dict(self.counters),
            "timings": self.timings[-100:],
            "last_updated": self.last_updated
        }
