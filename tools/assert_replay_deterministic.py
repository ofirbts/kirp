import json
from app.agent.agent import agent
from app.core.persistence import PersistenceManager

events = PersistenceManager.read_events(limit=100_000)

agent.reset()
for e in events:
    agent.apply_event(e)

state1 = agent.dump_state()

agent.reset()
for e in events:
    agent.apply_event(e)

state2 = agent.dump_state()

assert state1 == state2, "❌ Replay is NOT deterministic"
print("✅ Replay determinism verified")
