# app/scripts/replay_session.py
import json

from app.agent.agent import agent
from app.core.persistence import PersistenceManager


def main() -> None:
    print("=== FULL REPLAY SESSION ===")
    events = PersistenceManager.read_events(limit=100_000)

    agent.reset()

    for e in events:
        agent.apply_event(e)

    final_state = agent.dump_state()
    print("Replay completed.")
    print(json.dumps(final_state, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
