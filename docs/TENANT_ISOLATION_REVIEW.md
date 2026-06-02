# Tenant isolation review

Goal: trace **where tenant boundaries are enforced** vs **convention-only**, and list **cross-tenant leakage risks** with file evidence.

## Request routing and resolution

| Layer | Behavior | Isolation class |
| ----- | -------- | --------------- |
| JWT middleware | Sets `request.state.user` from payload `tenant_id`, `user_id`, `space_id` | **Hard** for authenticated requests |
| `get_tenant_context` | Refuses missing `tenant_id`/`user_id` in prod-like mode; `SKIP_AUTH` / local env injects `DEFAULT_LOCAL_CONTEXT` | **Soft** in dev (single shared default tenant) |
| `require_tenant_context` | Optional query param must match JWT or admin role | **Hard** when enforced |
| Webhooks (`v1_ingestion.py`) | Tenant from **env only** (`SLACK_WEBHOOK_*`, etc.) | **Hard** against body spoofing; **soft** if env mis-set (all traffic lands in one tenant) |

## Database filtering

### Mongo `EventStore`

| Method | Tenant filter | Risk |
| ------ | ------------- | ---- |
| `list` | Required unless `allow_all_tenants=True` | Low; `tenant_id='*'` raises unless admin flag |
| `find_latest_by_run_id` | `tenant_id` in query | Low |
| `find_by_external_id` / `update_by_external_id` | `tenant_id` in query | Low |
| `get_by_id` | **None** — lookup by `_id` only | **HIGH if UUID leaks**: any caller can read any tenant’s event |
| `count_events` | Optional `tenant_id`; if omitted, query `{}` suffix counts **all tenants** | **HIGH** if API passes `tenant_id=None` by mistake |

### Postgres `SchemaEngine`

| Operation | Tenant filter | Risk |
| --------- | ------------- | ---- |
| `get_node`, `list_nodes`, `upsert`, `delete_node` | `SchemaNode.tenant_id == tenant_id` in SQL | Low when callers pass JWT tenant |

### Governance API (`src/api/governance.py`)

| Route | Issue |
| ----- | ----- |
| `POST /governance/approve/{event_id}`, `reject` | Loads event via `get_by_id` **without** requiring `Request` or comparing JWT `tenant_id` to `ev.tenant_id`. Any authenticated user (or SKIP_AUTH dev user) who knows a UUID can approve/reject **another tenant’s** pending event. | **CRITICAL authorization gap** (storage is global read by id; **no tenant guard at HTTP layer**) |
| `GET /governance/approvals` | Without `tenant_id` query param uses `allow_all_tenants=True` → **cross-tenant listing** | **HIGH** unless route is admin-only (no Depends guard in file) |

## Cache partitioning

| Store | Key pattern | Tenant in key? |
| ----- | ----------- | --------------- |
| Redis idempotency | `idempotency:{key}` where key may be `idem:{client_key}` | **No** — **collision across tenants** if clients reuse keys |
| Redis run state | `tenant:{tenant_id}:{run_id}` | **Yes** |
| Run lookup | `run_lookup:{run_id}` | **No tenant in key** — mitigated by storing tenant_id value at write time |

## Vector isolation (Qdrant)

| Path | Enforcement |
| ---- | ----------- |
| `search` / `_single_hop_search` | `must` filter `tenant_id` MatchValue; rejects `tenant_id` empty or `*` |
| `upsert` | Rejects missing tenant; payload includes `tenant_id` |

**Residual risk:** mis-typed filter in future code paths; **UNVERIFIED** every alternate collection client.

## Event partitioning (Kafka)

| Aspect | Behavior |
| ------ | -------- |
| Message payload | Must include `tenant_id` / `user_id` for processor validation |
| Topic | Single topic `kirp-events` — isolation is **payload + consumer logic**, not separate topics per tenant |

## Webhook isolation

| Aspect | Behavior |
| ------ | -------- |
| Tenant choice | Env vars only — good for anti-spoofing |
| Multi-tenant SaaS on one URL | **Operational**: one webhook URL → one env tenant unless infra routes per tenant |

## Audit separation

| Path | Tenant |
| ---- | ------ |
| `AuditLog` rows | Include `tenant_id` column in model usage (`governance.log_audit`) |
| Log lines | String format includes tenant when provided |

## Background jobs and async

| Worker | Tenant source |
| ------ | ------------- |
| `kafka_processor` | Payload; invalid/missing tenant → reject processing |

---

## Summary: hard vs soft vs dangerous

| Class | Examples |
| ----- | -------- |
| **Hard** | Qdrant filter; `EventStore.list` default; schema SQL scoped queries; webhook env routing |
| **Soft** | SKIP_AUTH default tenant; Redis optional → weakened dedup |
| **Convention** | Callers must pass tenant into `count_events`; must not expose `get_by_id` to untrusted UUID |
| **Dangerous** | `get_by_id` without tenant; Redis idempotency key without tenant prefix; governance approve/reject without JWT tenant match; `count_events` with no tenant; approvals list with `tenant_id` omitted |

## Missing-filter leakage checklist (actionable)

1. **`EventStore.get_by_id`** — add `tenant_id` parameter and enforce on all API surfaces, **or** ensure only internal callers after authz check.
2. **`/governance/approve|reject`** — require `Request`, `get_tenant_context`, assert `ev.tenant_id == ctx.tenant_id` (or admin role).
3. **`GET /governance/approvals`** — default must not cross tenants without explicit admin dependency.
4. **Redis idempotency keys** — prefix with `tenant_id:` in `kafka_processor._get_event_idempotency_key` / `_mark_processed`.
5. **`count_events`** — consider requiring `tenant_id` non-optional for non-admin code paths (**UNVERIFIED** all call sites).
