import os
import requests
from app.agent.agent import agent

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")

def main():
    print("=== MEMORY GROWTH TEST ===")

    for i in range(200):
        requests.post(BASE + "/agent/query", json={"question": f"memory test {i}"})

    snapshot = agent.memory.snapshot()
    print("Short-term:", len(snapshot["short"]))
    print("Mid-term:", len(snapshot["mid"]))
    print("Long-term:", len(snapshot["long"]))

if __name__ == "__main__":
    main()
