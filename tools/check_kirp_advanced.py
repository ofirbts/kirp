import json
import os
import time
import requests
from pprint import pprint
from app.core.persistence import PersistenceManager
from app.agent.agent import agent
from deepdiff import DeepDiff

BASE = os.getenv("API_URL", "http://127.0.0.1:8000")

def section(title):
    print("\n" + "="*60)
    print(f"🔍 {title}")
    print("="*60)

def post(path, data):
    return requests.post(BASE + path, json=data)

def get(path):
    return requests.get(BASE + path)

def main():
    print("=== KIRP ADVANCED SYSTEM CHECK ===")

    # ---------------------------------------------------------
    section("Metrics")
    # ---------------------------------------------------------
    pprint(get("/debug/metrics").json())

    # ---------------------------------------------------------
    section("Policy Engine")
    # ---------------------------------------------------------
    print("Testing blocked ingest (too large)...")
    resp = post("/ingest", {"text": "A" * 20000})
    print("Status:", resp.status_code)
    print("Response:", resp.text)

    # ---------------------------------------------------------
    section("Knowledge Store")
    # ---------------------------------------------------------
    post("/ingest", {"text": "Knowledge test entry"})
    with open("storage/knowledge.json") as f:
        knowledge = json.load(f)
    print("Last knowledge entry:")
    pprint(knowledge[-1])

    # ---------------------------------------------------------
    section("Explainability Events")
    # ---------------------------------------------------------
    post("/agent/query", {"question": "What is the price?"})
    events = PersistenceManager.read_events(limit=10)
    print("Last events:")
    pprint(events)

    # ---------------------------------------------------------
    section("Self Evaluation")
    # ---------------------------------------------------------
    evaluation = agent.self_eval.evaluate(agent.dump_state())
    pprint(evaluation)

    # ---------------------------------------------------------
    section("Memory Tiering")
    # ---------------------------------------------------------
    pprint(agent.memory.snapshot())

    # ---------------------------------------------------------
    section("Replay Integrity")
    # ---------------------------------------------------------
    events = PersistenceManager.read_events(limit=200)
    print("Loaded events:", len(events))

    # ---------------------------------------------------------
    section("Agent Drift Detection")
    # ---------------------------------------------------------
    before = agent.dump_state()
    agent._state["total_queries"] += 1
    after = agent.dump_state()
    diff = DeepDiff(before, after, ignore_order=True)
    pprint(diff)

    print("\n=== DONE ===")

if __name__ == "__main__":
    main()
