import sys
import json
from datetime import datetime
from app.agent.agent import agent
from app.core.persistence import PersistenceManager


def parse_timestamp(ts_str: str) -> float:
    try:
        return float(ts_str)
    except:
        raise RuntimeError("Invalid timestamp. Use UNIX timestamp like 1736340000")


def main():
    # Optional timestamp argument
    until_ts = None
    if len(sys.argv) == 2:
        until_ts = parse_timestamp(sys.argv[1])
        print(f"⏱  Replaying until UNIX timestamp: {until_ts}")

    print("=== REPLAY UNTIL CHECKPOINT ===")

    events = PersistenceManager.read_events(limit=200_000)

    agent.reset()

    for e in events:
        # Convert ISO timestamp → UNIX timestamp
        ts = datetime.fromisoformat(e["timestamp"]).timestamp()

        # Stop if we passed the cutoff
        if until_ts is not None and ts > until_ts:
            break

        # IMPORTANT:
        # Do NOT apply knowledge_add events during replay.
        # They require embeddings and would call OpenAI.
        if e["type"] == "knowledge_add":
            continue

        agent.apply_event(e)

    print("=== Replay Completed ===")
    print(json.dumps(agent.dump_state(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
