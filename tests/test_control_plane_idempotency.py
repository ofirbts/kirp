from __future__ import annotations

import pytest

from src.control_plane.idempotency import redis_idempotency_key


def test_redis_idempotency_key_includes_tenant() -> None:
    assert redis_idempotency_key("t1", "idem:abc") == "idempotency:t1:idem:abc"


def test_redis_idempotency_key_strips_tenant_whitespace() -> None:
    assert redis_idempotency_key("  t2  ", "run:x") == "idempotency:t2:run:x"


def test_redis_idempotency_key_rejects_empty_tenant() -> None:
    with pytest.raises(ValueError):
        redis_idempotency_key("", "k")


def test_redis_idempotency_key_rejects_wildcard_tenant() -> None:
    with pytest.raises(ValueError):
        redis_idempotency_key("*", "k")
