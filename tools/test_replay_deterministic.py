def test_replay_deterministic():
    from app.agent.agent import agent
    from app.core.persistence import PersistenceManager

    events = PersistenceManager.read_events(limit=5000)

    agent.reset()
    for e in events:
        if e["type"] in ("agent_sync_decision", "agent_async_decision"):
            agent.apply_decision(e["payload"])

    state1 = agent.dump_state()

    agent.reset()
    for e in events:
        if e["type"] in ("agent_sync_decision", "agent_async_decision"):
            agent.apply_decision(e["payload"])

    state2 = agent.dump_state()

    assert state1 == state2
    print("✅ test_replay_deterministic passed")