# KIRP Enterprise — Audit Status

## Summary of Fixes Applied

### 1. Tenant/Space Context ("Scope: tenant not set / space all")
- **Cause:** Store started with `tenantId: undefined` when no tenant selected.
- **Fix:** Default `tenantId` to `"default"` in `tenantContextStore` when no value in localStorage.
- **Fix:** TopBar now sets `tenantId` to `"default"` when tenants list is empty.
- **Result:** Scope shows "tenant default" / "space all"; Events and other APIs receive `tenant_id: default`.

### 2. Hydration Warning (bis_skin_checked)
- **Cause:** Browser extensions (e.g. BitDefender, password managers) inject `bis_skin_checked` into DOM elements.
- **Fix:** Added `suppressHydrationWarning` to `CardTitle` in `components/ui/card.tsx`.
- **Result:** Warning suppressed. Root cause is external; cannot be removed without disabling extensions.

### 3. Brand OS / Monitoring (Optional Services)
- **Status:** Brand OS API (port 8002) and Monitoring (port 8001) are **optional**.
- **Behavior:** UI shows "Brand OS API is not running" when unavailable — expected.
- **To enable:** Start Brand OS service or set `NEXT_PUBLIC_BRAND_OS_API_URL`.

### 4. Events Page ("לא עובד")
- **Cause:** Events API requires `tenant_id`. With `tenantId: undefined`, backend uses context `default` from dev auth — should work.
- **Fix:** Default tenant to `"default"` so Events explicitly requests `tenant_id=default`.
- **Note:** If Events still empty, EventStore may have no events for tenant `default`. Run ingest first.

### 5. OPA Policy Enforcement
- **Status:** OPA (port 8181) returns 500 for full `/governance` document; `/governance/allow` works.
- **Backend:** Governance engine uses `/allow` endpoint — ingest/query work.
- **TEST_E2E:** Section 9 treats OPA as optional.

---

## Real vs Demo / Mock

| Component           | Status    | Notes                                                |
|---------------------|-----------|------------------------------------------------------|
| EventStore (MongoDB)| ✅ Real   | Persists events                                      |
| RAG (Qdrant)        | ✅ Real   | Vectors, search                                      |
| Agents              | ✅ Real   | Registered, runnable via API                         |
| Ingest/Query        | ✅ Real   | Full pipeline                                        |
| Kafka               | ✅ Real   | Produce/consume                                      |
| Tenants/Spaces      | ⚠️ Sparse | API exists; DB may be empty — returns `[]`          |
| Brand OS            | ⚠️ Optional | Not in docker-compose; separate service             |
| Monitoring          | ⚠️ Optional | Grafana on 3001; metrics from Prometheus           |
| OPA                 | ⚠️ Loaded | Policy loaded; direct curl may fail depending on path |
| system/ports, containers | ℹ️ Static | Next.js API routes — return mock data             |

---

## Services Not in docker-compose

- **Brand OS API** (8002)
- **Brand OS Monitoring** (8001) — Grafana is on 3001

---

## Recommended Next Steps

1. **Seed tenants:** Add at least one tenant to DB so TopBar dropdown is populated.
2. **Run ingest:** Ensure events exist for tenant `default` before expecting Events page data.
3. **Disable browser extensions** (or use incognito) to avoid `bis_skin_checked` if warning persists.
4. **Add favicon.ico** to `public/` if desired for production.
