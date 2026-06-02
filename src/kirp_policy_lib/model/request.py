from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


def _extract_roles(request_like: Mapping[str, Any]) -> tuple[str, ...]:
    for key in ("auth", "jwt", "claims", "user"):
        sub = request_like.get(key)
        if isinstance(sub, Mapping):
            r = sub.get("roles")
            if isinstance(r, (list, tuple)):
                return tuple(str(x).strip().lower() for x in r if x is not None and str(x).strip())
    r2 = request_like.get("roles")
    if isinstance(r2, (list, tuple)):
        return tuple(str(x).strip().lower() for x in r2 if x is not None and str(x).strip())
    return ()


class OperationType(str, Enum):
    READ = "read"
    MUTATION = "mutation"
    UNKNOWN = "unknown"


def _operation_from_method(method: str, mutation_methods: frozenset[str]) -> OperationType:
    m = method.upper()
    if m in mutation_methods:
        return OperationType.MUTATION
    if m in frozenset({"GET", "HEAD", "OPTIONS"}):
        return OperationType.READ
    return OperationType.UNKNOWN


@dataclass(frozen=True)
class RequestEnvelope:
    method: str
    path: str
    operation: OperationType
    explicit_mutating: bool | None
    roles: tuple[str, ...]
    extras: tuple[tuple[str, Any], ...]

    @staticmethod
    def from_mapping(
        request_like: Mapping[str, Any],
        *,
        mutation_methods: frozenset[str] | None = None,
    ) -> RequestEnvelope:
        mm = mutation_methods or frozenset({"POST", "PUT", "PATCH", "DELETE"})
        method = str(request_like.get("method", "GET")).upper()
        path = str(request_like.get("path", "/"))
        ex = request_like.get("mutating")
        explicit = bool(ex) if isinstance(ex, bool) else None
        if explicit is True:
            op = OperationType.MUTATION
        elif explicit is False:
            op = OperationType.READ
        else:
            op = _operation_from_method(method, mm)
        skip = frozenset({"method", "path", "mutating", "roles"})
        extras = tuple((k, v) for k, v in request_like.items() if k not in skip)
        return RequestEnvelope(
            method=method,
            path=path,
            operation=op,
            explicit_mutating=explicit,
            roles=_extract_roles(request_like),
            extras=extras,
        )

    def extras_dict(self) -> dict[str, Any]:
        return dict(self.extras)
