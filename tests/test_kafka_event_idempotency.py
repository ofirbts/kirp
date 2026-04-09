"""Kafka ingest idempotency key derivation — matches SYSTEM_STATUS Idempotency paths (Redis key prefix idempotency:{key})."""

from __future__ import annotations

import hashlib
import json

from src.workers.kafka_processor import _get_event_idempotency_key


def test_idempotency_explicit_top_level_wins() -> None:
    p = {"idempotency_key": "abc", "run_id": "run_x", "data": {"run_id": "ignored"}}
    assert _get_event_idempotency_key(p) == "idem:abc"


def test_idempotency_explicit_in_data() -> None:
    p = {"data": {"idempotency_key": "in-data"}}
    assert _get_event_idempotency_key(p) == "idem:in-data"


def test_idempotency_event_id_from_data() -> None:
    p = {"data": {"id": "ev-1"}, "run_id": "run_x"}
    assert _get_event_idempotency_key(p) == "event:ev-1"


def test_idempotency_run_id_top_level() -> None:
    p = {"run_id": "run_123", "trace_id": "tr_9"}
    assert _get_event_idempotency_key(p) == "run:run_123"


def test_idempotency_run_id_from_data_only() -> None:
    p = {"data": {"run_id": "run_from_data"}}
    assert _get_event_idempotency_key(p) == "run:run_from_data"


def test_idempotency_trace_id_when_no_run() -> None:
    p = {"trace_id": "tr_only"}
    assert _get_event_idempotency_key(p) == "trace:tr_only"


def test_idempotency_hash_fallback_stable() -> None:
    p = {"data": {"x": 1}}
    payload_str = json.dumps(p, sort_keys=True)
    expected = "hash:" + hashlib.sha256(payload_str.encode()).hexdigest()
    assert _get_event_idempotency_key(p) == expected
