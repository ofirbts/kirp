# Authorization boundary audit

**Scope:** HTTP routers under `src/api/`, services they call, worker `kafka_processor`, webhook ingress. **Classification:** SAFE / PARTIAL / DANGEROUS.

**Rule:** **DANGEROUS** = cross-tenant read/write plausible without tenant-bound credential OR body-supplied tenant trusted without JWT bind OR mutation by resource id only.

---

## 1. Tenant ownership checks

| Path / module | Classification | Evidence |
| ------------- | -------------- | -------- |
| `get_tenant_context` / `require_tenant_context` | **SAFE** (when used) | JWT-derived tenant; query override requires admin roles when implemented |
| `EventStore.list` | **SAFE** | Tenant required; `*` blocked unless `allow_all_tenants` |
| `SchemaEngine.get_node` / mutations | **SAFE** | SQL includes `SchemaNode.tenant_id == tenant_id` |
| `RAGEngine.search` / `upsert` | **SAFE** | Rejects missing tenant; Qdrant filter includes `tenant_id` |
| `EventStore.get_by_id` | **DANGEROUS** as a primitive | No tenant in query |
| `graph_service.get_node` / `get_neighbors` | **DANGEROUS** | `GraphNode.id == nid` only |
| `events_service.replay_event` | **PARTIAL → SAFE** | Loads `get_by_id` then **rejects** `ev.tenant_id != tenant_id` |
| `events_service.retry_dlq_event` | **DANGEROUS** | `retry_dlq` does not assert tenant on document |

---

## 2. Request ownership checks

| Route | Classification | Notes |
| ----- | -------------- | ----- |
| `POST /api/v1/ingest` | **SAFE** | Uses `get_tenant_context(request)` only |
| `POST /api/v1/execute` and approve/reject | **DANGEROUS** | No `Depends` auth in `v1_execute.py`; tenant from **body** or from stored doc without JWT match |
| `POST /governance/approve/{event_id}` | **DANGEROUS** | No `Request`; no tenant match to event |
| `GET /api/graph/nodes/{node_id}` | **DANGEROUS** | No `TenantContext` Depends |
| `GET /api/v1/graph` | **SAFE** | `get_tenant_context(request)` + mismatch check on query tenant |

---

## 3. Event ownership checks

| Operation | Classification |
| --------- | -------------- |
| Kafka `validate_ingest_tenant_context` | **SAFE** for processor path |
| Governance approve/reject | **DANGEROUS** |
| Events replay (`/api/events/{id}/replay`) | **SAFE** (tenant mismatch → ValueError) |
| DLQ retry | **DANGEROUS** |

---

## 4. Admin privilege boundaries

| Surface | Classification | Notes |
| ------- | -------------- | ----- |
| `GET /governance/approvals` without `tenant_id` | **DANGEROUS** | Cross-tenant list via `allow_all_tenants=True` |
| `require_tenant_context(..., allow_cross_tenant_roles=["admin"])` | **PARTIAL** | Correct pattern when applied; **UNVERIFIED** coverage on all admin routes |

---

## 5. Async worker trust boundaries

| Boundary | Classification | Notes |
| -------- | -------------- | ----- |
| Kafka payload `tenant_id` | **PARTIAL** | Validated in processor; **trust model** = broker + producers allowed on network |
| Redis idempotency keys | **DANGEROUS** | Global namespace; see risk register |

---

## 6. Webhook trust boundaries

| Surface | Classification | Notes |
| ------- | -------------- | ----- |
| Tenant from env | **SAFE** against body spoofing |
| Kafka publish unchecked | **DANGEROUS** for **integrity** of “accepted” signal |

---

## 7. Internal vs external APIs

| API family | Trust model |
| ---------- | ----------- |
| `/api/v1/*` with `get_tenant_context` | External user; must not trust body tenant |
| `/api/graph/*` legacy | **Treat as external**; missing Depends is a defect |
| Worker internal calls | Trust Kafka ACLs + network segmentation |

---

## 8. Queue consumer assumptions

| Assumption | Risk |
| ---------- | ---- |
| Message contains honest `tenant_id` | Compromised producer = cross-tenant write; **mitigate** with mTLS / ACLs / signing **UNVERIFIED** in repo |

---

## Routes / workflows: cross-tenant access

| ID | Workflow |
|----|----------|
| X-1 | `GET /api/graph/nodes/{id}` and neighbors |
| X-2 | `GET /governance/approvals` without `tenant_id` |
| X-3 | `EventStore.get_by_id` used without subsequent tenant check |
| X-4 | `POST /api/events/dlq/{id}/retry` via `retry_dlq` path |

## Unauthorized mutation

| ID | Workflow |
|----|----------|
| M-1 | `POST /governance/approve/{event_id}` / `reject` |
| M-2 | `POST /api/v1/execute` with body tenant |
| M-3 | `POST /api/v1/execute/approve/{pending_id}` without JWT tenant bind |

## Replay abuse

| ID | Workflow |
|----|----------|
| P-1 | Webhook + provider retries + unchecked Kafka emit |
| P-2 | Stripe webhook without `event.id` dedup store (**partial** harm; lifecycle idempotent) |

## Privilege escalation

| ID | Workflow |
|----|----------|
| E-1 | Non-admin calling cross-tenant approvals list |
| E-2 | Body `tenant_id` on execute if auth missing |

---

## Summary

**DANGEROUS count (non-exhaustive grep pass):** governance mutate, legacy graph node read, execute family auth gap, DLQ retry service path, Redis idempotency global keys, webhook false success.

**UNVERIFIED:** Full enumeration of every `src/api/*.py` router line-by-line; recommend automated OpenAPI + auth matrix generation as follow-on.
