from typing import Dict, Any
from app.core.persistence import PersistenceManager


class StateSnapshotter:
    """
    Emits full agent state snapshots every N events
    to allow fast, deterministic replay checkpoints.
    """

    def __init__(self, every_n_events: int = 50) -> None:
        self.every_n_events = every_n_events
        self._counter = 0

    def maybe_snapshot(self, agent) -> None:
        self._counter += 1
        if self._counter % self.every_n_events != 0:
            return

        snapshot = agent.dump_state()
        PersistenceManager.append_event(
            "agent_state_snapshot",
            {"state": snapshot},
        )
