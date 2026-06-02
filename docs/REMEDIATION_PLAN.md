# Remediation plan — P0 / P1

**No code changes in this document.** Each item lists **exact locations**, **required fix**, **tests**, **rollout**, **rollback**.

---

## R-001 — Governance approve/reject tenant bind

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/api/governance.py`: `approve_event`, `reject_event` (lines using `store.get_by_id`) |
| **Required fix** | Inject `Request`; `ctx = get_tenant_context(request)`; after `ev = await store.get_by_id(...)`, if `ev.tenant_id != ctx.tenant_id` and user lacks global-admin role → **403**. Optionally require `space_id` match if product demands. |
| **Architecture** | Governance becomes explicitly **user-scoped**, not “Mongo UUID oracle.” |
| **Migration** | Breaking for any **intentional** cross-tenant admin use; preserve via **named admin role** only. |
| **Rollout** | Deploy behind feature flag `STRICT_GOVERNANCE_TENANT=1` if you need gradual enable. |
| **Regression** | Approve own-tenant event still 200; cross-tenant 403. |
| **Tests** | Integration: two JWTs, two pending events; negative cross-approve. |
| **Observability** | `log_json` `governance_approve_denied_tenant_mismatch` with `tenant_id`, `event_tenant_id`, `event_id`. |
| **Deploy** | No schema migration. |
| **Rollback** | Disable flag or revert handler. |

---

## R-002 — `get_by_id` primitive

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/core/event_store.py` `get_by_id`; all callers (`grep get_by_id` in `src/`) |
| **Required fix** | Add `get_by_id_for_tenant(event_id, tenant_id)` or require `tenant_id` kw-only on `get_by_id`; update governance, processor (pass validated tenant), any other caller. |
| **Architecture** | Single enforced primitive prevents future IDOR regressions. |
| **Migration** | Mechanical refactor; highest risk in **worker** if tenant extracted wrong from payload. |
| **Tests** | Unit: wrong tenant → `None` or raises. |
| **Observability** | Optional metric `event_get_by_id_tenant_mismatch_total`. |

---

## R-003 — Redis idempotency key namespace

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/workers/kafka_processor.py`: `_get_event_idempotency_key`, `_check_idempotency`, `_mark_processed` |
| **Required fix** | After tenant validated, prefix: `f"{tenant_id}:{key}"` for Redis ops only. |
| **Regression** | Old keys TTL out (1h); during rollout expect **duplicate processing** window unless dual-write dual-check. |
| **Rollout** | Dual-check: `old_key OR new_key` for one release, then remove old. |
| **Tests** | Unit: two tenants same explicit idempotency key both process. |

---

## R-004 — Webhook Kafka emit

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/api/v1_ingestion.py`: `_ingest_one`, Notion loop, Slack loop |
| **Required fix** | `if not KafkaEventAgent().emit(...): raise HTTPException(503, ...)` or accumulate per-item failures in response. |
| **Tests** | Integration with broker stopped: expect **503** or per-item `ok: false`. |

---

## R-005 — Legacy graph node routes

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/api/graph.py` `get_graph_node`, `get_graph_node_neighbors`; `src/services/graph_service.py` `get_node`, `get_neighbors` |
| **Required fix** | Add `ctx: TenantContext = Depends(get_effective_tenant_context)`; pass `ctx.tenant_id` into service; SQL `AND GraphNode.tenant_id == :tid`. |
| **Tests** | API: tenant A cannot read B’s node UUID. |

---

## R-006 / R-012 — Execute API auth + tenant bind

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/api/v1_execute.py`: all handlers |
| **Required fix** | `Depends(require_auth)` or equivalent; derive `tenant_id`/`user_id` from JWT; **remove** client-settable tenant except for documented admin route. On approve/reject, assert `doc["tenant_id"] == ctx.tenant_id`. |
| **Tests** | Unauthenticated → 401; wrong tenant body → 403; approve other pending → 403. |

---

## R-007 — DLQ retry tenant check

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/services/events_service.py` `retry_dlq_event`; `src/core/event_store.py` `retry_dlq` |
| **Required fix** | Load doc; `Event.from_doc`; if `ev.tenant_id != tenant_id` raise `ValueError` (same as replay). |
| **Tests** | Mirror `replay_event` negative test. |

---

## R-008 — Governance approvals list

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/api/governance.py` `get_pending_approvals` |
| **Required fix** | Remove default cross-tenant branch; require `tenant_id` query **or** admin `Depends` with audit log. |
| **Tests** | Non-admin without tenant → 400/403. |

---

## R-009 — OPA fail-open

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/core/governance.py` `__init__` / `check`; `src/main.py` startup |
| **Required fix** | In `ENV=production`, require non-empty `OPA_URL` **or** explicit `ALLOW_GOVERNANCE_FAIL_OPEN=0` contract. |
| **Tests** | Startup test in staging config. |

---

## R-013 — Processor DLQ

| Field | Detail |
| ----- | ------ |
| **Locations** | `src/workers/kafka_processor.py` terminal failure path; `EventStore.move_to_dlq` |
| **Required fix** | On max retries exceeded, `move_to_dlq` + commit offset (policy choice: skip poison) **must be documented**; ops runbook link. |
| **Tests** | Integration with broken handler: message lands in `dlq_events`. |

---

## Dependency order (recommended)

1. R-006 / R-012 (execute auth) — stops remote blast radius.  
2. R-001 / R-008 (governance) — stops cross-tenant governance mutation/list.  
3. R-005 / R-007 / R-002 (read paths) — closes IDOR class.  
4. R-003 (Redis keys) — closes dedup collision.  
5. R-004 / R-013 / R-009 (operational honesty + poison + OPA).
