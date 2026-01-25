import psutil
import time

START = time.time()

def get_metrics():
    return {
        "uptime": time.time() - START,
        "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
        "qps": 0.0,
        "drift": 0.0,
    }
