import json
import sys
from app.agent.agent import Agent   
from app.core.persistence import PersistenceManager

if len(sys.argv) != 2:
    print("Usage: python replay_session.py <session_id>")
    sys.exit(1)

session_id = sys.argv[1]

session = PersistenceManager.load_session(session_id)
if not session:
    raise RuntimeError("Session not found")

events = PersistenceManager.read_events(limit=10_000)

agent = Agent()

# חובה: reset() — אתה צריך להוסיף אותו ל־Agent
agent.reset()

print(f"🔁 Replaying session {session_id}")

for event in events:
    payload = event["payload"]

    if payload.get("session_id") != session_id:
        continue

    if event["type"] == "agent_decision":
        agent.apply_decision(payload)

print("✅ Replay finished")
print("Final agent state:")
print(json.dumps(agent.dump_state(), indent=2))
