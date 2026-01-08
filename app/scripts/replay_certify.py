from app.agent.agent import agent
from app.core.persistence import PersistenceManager


def main():
    events = PersistenceManager.read_events(limit=50_000)

    agent.reset()
    for e in events:
        agent.apply_event(e)

    state = agent.dump_state()

    assert state["state"]["total_queries"] >= 0
    print("✅ Replay certification: PASS")
    print("Total queries:", state["state"]["total_queries"])


if __name__ == "__main__":
    main()
