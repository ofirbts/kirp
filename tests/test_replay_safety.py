from __future__ import annotations

from src.control_plane.verification.chaos_engine import ChaosEngine
from src.control_plane.verification.replay_tests import replay_events_ordered_ids, replay_events_single_tenant


def test_replay_single_tenant_ok() -> None:
    ok, err = replay_events_single_tenant([{"tenant_id": "a"}, {"tenant_id": "a"}])
    assert ok and err is None


def test_replay_single_tenant_mixed() -> None:
    ok, err = replay_events_single_tenant([{"tenant_id": "a"}, {"tenant_id": "b"}])
    assert not ok and err == "mixed_tenant_replay"


def test_replay_ordered_ids_ok() -> None:
    ok, err = replay_events_ordered_ids([{"id": "a"}, {"id": "b"}])
    assert ok and err is None


def test_replay_ordered_ids_fail() -> None:
    ok, err = replay_events_ordered_ids([{"id": "b"}, {"id": "a"}])
    assert not ok and err == "out_of_order"


async def test_chaos_engine_disabled_no_sleep() -> None:
    eng = ChaosEngine(enabled=False)
    await eng.maybe_delay_ms(50)
