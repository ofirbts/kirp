from __future__ import annotations

import pytest

from src.core.integrations import _kafka_bootstrap


def test_kafka_bootstrap_maps_localhost_9092_to_9093(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    assert _kafka_bootstrap() == "localhost:9093"


def test_kafka_bootstrap_keeps_explicit_9093(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9093")
    assert _kafka_bootstrap() == "localhost:9093"


def test_kafka_bootstrap_docker_default_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KAFKA_BOOTSTRAP_SERVERS", raising=False)
    assert _kafka_bootstrap() == "kafka:9092"


def test_local_kafka_processor_defaults_to_host_port_9093() -> None:
    from pathlib import Path

    script = Path(__file__).resolve().parents[1] / "scripts" / "run_local_kafka_processor.sh"
    text = script.read_text(encoding="utf-8")
    assert "localhost:9093" in text
    assert "localhost:9092" not in text
