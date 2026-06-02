"""Kafka wire envelope: producer dict shape, consumer flattening, ingest validation."""

from __future__ import annotations

from src.models.kafka_wire_envelope import (
    build_kafka_emit_dict,
    flatten_kafka_envelope_to_event_data,
    validate_ingest_tenant_context,
)


def test_build_emit_dict_matches_expected_keys() -> None:
    d = build_kafka_emit_dict(
        event_type="ingest.v1",
        data={"content": "x"},
        tenant_id="t1",
        space_id="s1",
        user_id="u1",
        run_id="r1",
        workflow_type="ingest",
        trace_id="tr1",
        idempotency_key="ik1",
        parent_run_id="p1",
    )
    assert d["type"] == "ingest.v1"
    assert d["data"] == {"content": "x"}
    assert d["tenant_id"] == "t1"
    assert d["space_id"] == "s1"
    assert d["user_id"] == "u1"
    assert d["run_id"] == "r1"
    assert d["workflow_type"] == "ingest"
    assert d["trace_id"] == "tr1"
    assert d["idempotency_key"] == "ik1"
    assert d["parent_run_id"] == "p1"


def test_flatten_prefers_top_level_tenant_space_user_when_not_none() -> None:
    payload = {
        "type": "ingest.v1",
        "tenant_id": "top_t",
        "space_id": "top_s",
        "user_id": "top_u",
        "data": {"tenant_id": "inner_t", "foo": 1},
    }
    merged = flatten_kafka_envelope_to_event_data(payload)
    assert merged["tenant_id"] == "top_t"
    assert merged["space_id"] == "top_s"
    assert merged["user_id"] == "top_u"
    assert merged["foo"] == 1


def test_flatten_run_fields_use_top_level_or() -> None:
    payload = {
        "type": "ingest.v1",
        "tenant_id": "t",
        "space_id": "s",
        "user_id": "u",
        "data": {"run_id": "from_inner", "trace_id": "tr_inner"},
    }
    merged = flatten_kafka_envelope_to_event_data(payload)
    assert merged["run_id"] == "from_inner"
    assert merged["trace_id"] == "tr_inner"

    payload2 = {
        "type": "ingest.v1",
        "tenant_id": "t",
        "space_id": "s",
        "user_id": "u",
        "run_id": "top_run",
        "data": {"run_id": "inner_ignored_when_top_truthy"},
    }
    merged2 = flatten_kafka_envelope_to_event_data(payload2)
    assert merged2["run_id"] == "top_run"


def test_flatten_non_dict_data_becomes_empty_overlay() -> None:
    payload = {"type": "ingest.v1", "tenant_id": "t", "space_id": "s", "user_id": "u", "data": "bad"}
    merged = flatten_kafka_envelope_to_event_data(payload)
    assert merged["tenant_id"] == "t"
    assert "bad" not in merged


def test_emit_then_flatten_roundtrip_inner_payload() -> None:
    inner = {"text": "hello", "source": "api"}
    wire = build_kafka_emit_dict(
        event_type="ingest.v1",
        data=inner,
        tenant_id="ta",
        space_id="sp",
        user_id="us",
        run_id="run_z",
    )
    merged = flatten_kafka_envelope_to_event_data(wire)
    assert merged["text"] == "hello"
    assert merged["source"] == "api"
    assert merged["tenant_id"] == "ta"
    assert merged["run_id"] == "run_z"


def test_validate_ingest_tenant_context() -> None:
    assert validate_ingest_tenant_context({"tenant_id": "t", "user_id": "u"}) is None
    assert validate_ingest_tenant_context({"tenant_id": "*", "user_id": "u"}) == "invalid_tenant"
    assert validate_ingest_tenant_context({"tenant_id": "", "user_id": "u"}) == "invalid_tenant"
    assert validate_ingest_tenant_context({"tenant_id": "t", "user_id": ""}) == "missing_user_id"
    assert validate_ingest_tenant_context({"tenant_id": "t"}) == "missing_user_id"
