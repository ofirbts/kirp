# Phase 1 Scope & Cloud Deployment

## What the system currently does

- **Event-sourced ingest**: Content is ingested via `POST /api/v1/ingest`; events are stored in MongoDB, embedded via OpenAI, and indexed in Qdrant.
- **RAG**: `POST /api/v1/query` returns context and answers over tenant/space-scoped knowledge.
- **Governance**: All writes go through the governance engine; multi-tenant isolation (tenant_id, space_id, user_id) is enforced.
- **Agents**: Registered agents (planner, schema structure, presentation, etc.) can be triggered manually or by triggers.
- **Dashboard**: Next.js UI shows Mission Control, Observability, Agents, Events, Tasks, Decisions, Graph, and more.

---

## What Phase 1 includes

1. **EventPipeline → SchemaEngine (life objects)**  
   After every ingest, the pipeline extracts life objects (Task by default), parses optional due dates from content, and calls `SchemaEngine.upsert_node`. Every relevant event creates or updates a schema node.

2. **Notion connector (pull → ingest)**  
   `POST /api/v1/notion/sync` pulls pages from the Notion database (`NOTION_TASKS_DB_ID`). Idempotent by `external_id` + source; new pages flow through the full ingest pipeline.

3. **Tasks API**  
   `GET /api/v1/tasks?tenant_id=...&space_id=...` returns tasks from SchemaEngine (id, title, due_date, source, status, etc.).

4. **Tasks UI**  
   Page `/tasks` with table (title, due_date, source, status), filters, and timeline sort.

5. **CommandExecutor → Notion**  
   Approved tasks can create entries in Notion via `NotionIntegration.create_task`.

---

# Full cloud deployment flow

Goal: **API on RunMyDocker (from a Docker image), UI on Vercel (from GitHub), Tasks page and Notion sync working in production.**

---

## 1. API on RunMyDocker (run from Docker image)

The API **must run from a Docker image** (not Git clone). Build the image locally or in CI, push to a registry, then RunMyDocker runs that image.

### 1.1 Build the Docker image locally

From the **repository root** (where `Dockerfile.api` and `requirements.txt` live):

```bash
# Build the API image (build context = repo root)
docker build -f Dockerfile.api -t kirp-api:latest .

# Optional: tag for your registry (e.g. Docker Hub, GHCR)
# docker tag kirp-api:latest your-registry/kirp-api:latest
```

- **Dockerfile**: `Dockerfile.api`
- **Context**: repo root (so `COPY . .` includes `src/`, `requirements.txt`, etc.)
- **Result**: image that runs `uvicorn src.main:app --host 0.0.0.0 --port 8000`
- **Port**: the API **listens on port 8000** (EXPOSE 8000 + CMD). RunMyDocker must map/expose 8000.

### 1.2 Upload the image to RunMyDocker

- **Option A — Push to a registry, then use image in RunMyDocker**  
  1. Push the image to Docker Hub, GitHub Container Registry (GHCR), or another registry RunMyDocker supports.  
  2. In RunMyDocker, create a new service that runs **your image** (e.g. `your-registry/kirp-api:latest`), not a Git clone.  
  3. Set the container to listen on **port 8000** (usually the default when you expose 8000 in the image).

- **Option B — RunMyDocker “build from Dockerfile”**  
  If your RunMyDocker setup builds from the repo’s Dockerfile, set **Dockerfile path** to `Dockerfile.api` and **build context** to repo root, then deploy. The resulting image is the same; ensure the running container exposes port 8000.

### 1.3 Environment variables (RunMyDocker)

Use the same variables as in **`.env.example`** (repo root). Set them in RunMyDocker’s env configuration (not in the image).

**Required for a working deployment:**

| Variable | Description |
|----------|-------------|
| `CORS_ORIGINS` | Comma-separated list of UI origins, e.g. `https://your-app.vercel.app` (must match the Vercel URL exactly, no trailing slash). |
| `MONGO_URI` | MongoDB connection string (e.g. Atlas). |
| `POSTGRES_URI` | PostgreSQL connection string (e.g. `postgresql+asyncpg://user:pass@host:5432/kirp`). |
| `QDRANT_URL` | Qdrant URL (and `QDRANT_API_KEY` if required). |
| `OPENAI_API_KEY` | OpenAI API key (for RAG and agents). |

**For Notion sync and Tasks:**

| Variable | Description |
|----------|-------------|
| `NOTION_TOKEN` | Notion integration token. |
| `NOTION_TASKS_DB_ID` | Notion database ID for tasks. |

**Optional:** `SKIP_AUTH=1` or `DEV_TOKEN=<token>` for simple auth; `JWT_SECRET` for production JWT.

### 1.4 CORS and port

- **CORS**: The API reads `CORS_ORIGINS` and allows those origins. Set it to your Vercel app URL (e.g. `https://kirp-xyz.vercel.app`). Multiple origins: comma-separated. This is required for the browser to call the API from the Vercel UI.
- **Port**: The API listens on **port 8000** inside the container. RunMyDocker should expose this port so the API is reachable at `https://your-api.runmydocker.com` (or your assigned URL).

### 1.5 Verify API

- `GET https://your-api.runmydocker.com/healthz` → `{"status":"ok",...}`
- `GET https://your-api.runmydocker.com/health` → checks EventStore + RAG (may 503 if backends not configured yet).

---

## 2. UI on Vercel (deploy from GitHub)

The Next.js app must work when **deployed from GitHub** and call the production API.

### 2.1 Connect GitHub and deploy

1. In [Vercel](https://vercel.com), **Add New Project** and import your **GitHub repository**.
2. **Root Directory**: leave as repo root (the app uses `app/`, `lib/`, `components/` at root).
3. **Framework**: Vercel should detect Next.js.
4. Do **not** build from a subdirectory; the Next.js app lives at the repo root.

### 2.2 Environment variables (Vercel)

In **Project → Settings → Environment Variables**, set:

| Variable | Value | Notes |
|----------|--------|--------|
| `NEXT_PUBLIC_API_URL` | `https://your-api.runmydocker.com` | Your RunMyDocker API URL, **no trailing slash**. Required so the UI calls the production API. |
| `NEXT_PUBLIC_DEV_TOKEN` | (optional) | Same as API’s `DEV_TOKEN` if you use token auth. |

All API requests from the dashboard use `NEXT_PUBLIC_API_URL` (see `lib/apiClient.ts`). There are no hardcoded production URLs; the only fallback is `http://localhost:8000` when the env is unset (local dev).

### 2.3 Clean env example for Vercel

Use **`docs/env.local.example`** (or the content below) as a reference. In Vercel you set the variables in the dashboard, not in a file.

```
# Production (set in Vercel)
NEXT_PUBLIC_API_URL=https://your-api.runmydocker.com
# NEXT_PUBLIC_DEV_TOKEN=your-token
```

### 2.4 Build and deploy

- Trigger a deploy (push to main or “Redeploy” in Vercel).
- After deploy, the app runs at `https://your-app.vercel.app` (or your custom domain). All dashboard pages (including **Tasks**) call the API at `NEXT_PUBLIC_API_URL`.

---

## 3. Connect API and UI

1. **API (RunMyDocker)**  
   - Set `CORS_ORIGINS` to your Vercel origin, e.g. `https://your-app.vercel.app`.  
   - If you use preview deployments, you can add `https://*-your-team.vercel.app` or each preview URL as needed.

2. **UI (Vercel)**  
   - Set `NEXT_PUBLIC_API_URL` to the RunMyDocker API URL (e.g. `https://kirp-xxx.runmydocker.com`).

3. **Result**  
   - Open the Vercel app → **Tasks** page: it should load tasks from `GET /api/v1/tasks` (real data from SchemaEngine).  
   - **Notion sync**: call `POST /api/v1/notion/sync` (e.g. with curl, or add a “Sync Notion” button in the UI). With `NOTION_TOKEN` and `NOTION_TASKS_DB_ID` set in the API, sync will pull Notion pages and create/update tasks.

---

## 4. Summary checklist

| Step | Action |
|------|--------|
| 1 | Build image: `docker build -f Dockerfile.api -t kirp-api:latest .` |
| 2 | Push image to your registry (if RunMyDocker runs from registry). |
| 3 | In RunMyDocker: run the API from that image, expose port **8000**. |
| 4 | In RunMyDocker: set env from `.env.example` / `.env` (including `CORS_ORIGINS` = your Vercel URL). |
| 5 | In Vercel: connect GitHub repo, root = repo root. |
| 6 | In Vercel: set `NEXT_PUBLIC_API_URL` to RunMyDocker API URL. |
| 7 | Deploy UI; open Tasks page and confirm real data; run Notion sync if configured. |

---

## Reference: env files

- **API (RunMyDocker):** `.env.example` (copy to `.env`) — all required variables and CORS.
- **UI (Vercel):** `docs/env.local.example` — `NEXT_PUBLIC_API_URL` and optional `NEXT_PUBLIC_DEV_TOKEN`.

The system is fully deployable in the cloud: API on RunMyDocker (from image, port 8000), UI on Vercel (from GitHub), with Tasks page and Notion sync working in production when the listed env vars are set.

---

## Troubleshooting

### "password authentication failed for user 'neondb_owner'" (PostgreSQL / Neon)

SchemaEngine uses `POSTGRES_URI` for tasks and life-object storage. If you see this error on ingest or `GET /api/v1/tasks`:

1. **Neon dashboard**: Open your Neon project → Connection details. Copy the connection string (or note user/password).
2. **Password**: If you rotated the password in Neon, update `POSTGRES_URI` in `.env` with the new password. The app does not cache credentials beyond the connection pool.
3. **URI format for asyncpg**: Use `postgresql+asyncpg://user:password@host:5432/dbname?sslmode=require` (Neon often requires SSL). Replace `user`/`password`/`host`/`dbname` with the values from Neon.
4. Restart the API after changing `.env` so the SchemaEngine picks up the new URI.
