# Unified KIRP UI — Validation Guide

After repair and stabilization, use this to verify the UI and backend.

## Prerequisites

- **Backend (KIRP API):** Run with dev auth so the UI gets 200 (not 401).
  - Option A: `ENV=development uvicorn src.main:app --host 0.0.0.0 --port 8000`
  - Option B: `SKIP_AUTH=1 uvicorn src.main:app --host 0.0.0.0 --port 8000`
  - Option C: Set `DEV_TOKEN` on backend and `NEXT_PUBLIC_DEV_TOKEN` in UI `.env.local` (same value).
- **UI:** `npm install && npm run dev` (port 3100).

## 1. UI loads without errors

```bash
npm run dev
# Open http://localhost:3100 — should redirect to /dashboard, no ENOENT or 401 in browser console.
```

## 2. All pages load

Open each in the browser (or use the validation script):

| Route | Description |
|-------|-------------|
| /dashboard | Dashboard |
| /mission-control | Mission Control |
| /system-control | System Control |
| /agents | Agents |
| /events | Events |
| /pipeline | Pipeline |
| /content | Content |
| /visuals | Visuals |
| /signals | Signals |
| /run | Run |
| /history | History |
| /dev | Dev Mode |
| /tenants | Tenants |
| /observability | Observability |
| /decisions | Decisions |
| /graph | Knowledge Graph |
| /governance/audit | Audit |

## 3. All API endpoints return 200

- **Next.js API (same origin):** `/api/health`, `/api/agents`, `/api/history`, `/api/visuals`, `/api/system/ports`, `/api/system/containers`, `/api/brand/templates`, `/api/brand/memory`.
- **Backend (8000):** `/health`, `/api/v1/stats`, `/api/tenants`, `/api/events`, `/api/agents`, `/api/decisions`, `/api/graph`, `/api/audit` — require backend running with dev auth (see above).

## 4. No 401 or 404

- **401:** Backend returns "Authentication required" if `request.state.user` is not set. Fix: run backend with `SKIP_AUTH=1` or `ENV=development`, or set `NEXT_PUBLIC_DEV_TOKEN` and backend `DEV_TOKEN`.
- **404:** Backend 404 on `/api/tenants`, `/api/events`, etc. — ensure routers are included in `src/main.py` (tenants, decisions, graph, audit_api) and restart API.

## 5. No ENOENT errors

- Next.js must not scan `brand_os_ui` (folder removed). `tsconfig.json` excludes `brand_os_ui`.
- No references to `brand_os_ui` in `package.json`, `next.config.js`, or scripts.

## 6. kirp-agent-processor stays UP

- **Cause of crash:** `FileNotFoundError: /tmp/prometheus/gauge_all_1.db` — Prometheus multiprocess dir missing in container.
- **Fix:** `Dockerfile.agent` creates `/tmp/prometheus` and sets `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus`.
- **Verify:** `docker compose up -d kirp-agent-processor && docker logs kirp-agent-processor` — no traceback.

## 7. Mission Control shows correct health

- Open `/mission-control`. Services: kirp-api, brand_os_api, brand_os_monitoring, qdrant, opa.
- kirp-api: OK when backend is up on 8000.
- qdrant, redis, postgres, kafka, monitoring: OK when respective services are running.

## Run validation script

```bash
chmod +x scripts/validate_ui.sh
./scripts/validate_ui.sh http://localhost:3100 http://localhost:8000
```

Exits 0 if all UI and Next.js API checks pass; backend checks are optional (warn only if down).
