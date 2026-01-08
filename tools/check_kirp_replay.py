import json
from app.agent.agent import agent
from app.core.persistence import PersistenceManager

def main():
    print("=== REPLAY DETERMINISM TEST ===")

    before = agent.dump_state()

    events = PersistenceManager.read_events(limit=5000)

    agent.reset()

    for e in events:
        if e["type"] in ("agent_sync_decision", "agent_async_decision"):
            agent.apply_decision(e["payload"])

    after = agent.dump_state()

    print("Before:")
    print(json.dumps(before, indent=2))
    print("\nAfter:")
    print(json.dumps(after, indent=2))

    print("\nDeterministic:", before == after)

if __name__ == "__main__":
    main()
