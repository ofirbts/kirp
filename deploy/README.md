# Deploy — run the stack locally (prod-style)

**Goal:** API + Postgres + Redis + Mongo on your machine (e.g. WSL + Docker), with a repeatable smoke check.

---

## 1. Prerequisites

- **Docker Desktop** running; on Windows, enable **WSL integration** for your distro: *Settings → Resources → WSL integration* → enable distro → Apply & Restart.

Verify:

```bash
docker --version
docker compose version
```

---

## 2. Environment (`.env.prod`)

- Template: `deploy/.env.prod.example` → copy to **repo root** `.env.prod` and fill real values.
- **Important:** `launch-prod.sh` **overwrites** root `.env.prod` from the example every time. If you already edited `.env.prod`, either back it up first or skip `launch-prod.sh` and use the commands in §4.

**Production fail-fast (see `src/main.py`):** in `ENV=production`, these must be non-empty where applicable:

- `STRIPE_SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`

**Inside Docker**, DB URLs must use **service names**, not `localhost`:

| Variable | Typical value in this compose |
|----------|------------------------------|
| `DATABASE_URL` / `POSTGRES_URI` | `postgresql+asyncpg://kirp_user:kirp_password@postgres:5432/kirp` (match your `.env.prod`) |
| `REDIS_URL` | `redis://redis:6379/0` |
| `MONGO_URI` | `mongodb://mongo:27017/kirp` |

If the API container uses `localhost` for Mongo/Postgres, health will stay **503** — fix the URI to the hostname above.

---

## 3. One-command launch (overwrites `.env.prod`)

From **repo root**:

```bash
./deploy/launch-prod.sh
```

This copies `deploy/.env.prod.example` → `.env.prod`, runs `docker compose -f deploy/docker-compose.prod.yml up -d --build`, then `deploy/smoke-test.sh`.

---

## 4. Manual flow (keeps your `.env.prod`)

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
./deploy/smoke-test.sh
```

---

## 4b. One-shot dashboard user + API checks (no Docker rebuild)

With the stack already up and **curl** available on the host:

```bash
./deploy/local-dashboard-verify.sh
```

Creates a **new** user (unique email by default), checks `signup` → `auth/me` → `stats` with JWT.  
Use your own test identity:

```bash
VERIFY_EMAIL='you@example.com' VERIFY_PASSWORD='YourPassw0rd!' VERIFY_NAME='You' ./deploy/local-dashboard-verify.sh
```

Then sign in at `http://localhost:3100/login` with the same email/password.

## 4c. One-shot ingest → Kafka → pipeline

Requires a stack where **Kafka is reachable from the API** and the **`kirp-agent-processor`** consumer is running.

- **`deploy/docker-compose.prod.yml`** includes **Kafka**, **Zookeeper**, and **`kirp-agent-processor`** (see that file). Use it with a correct `KAFKA_BOOTSTRAP_SERVERS` / broker hostname for where the API runs (e.g. `kafka:9092` inside Compose, or host port mapping from the host).
- If the API process has **no working producer** (wrong bootstrap, broker down, missing `confluent-kafka`), `POST /api/v1/ingest` returns **503** — the verify script treats that as exit **3** (“no event bus”).

```bash
./deploy/verify-ingest-e2e.sh
# or against another API URL:
KIRP_VERIFY_API_URL=http://localhost:8080 ./deploy/verify-ingest-e2e.sh
```

Success line: `INGEST_E2E_OK`. Exit **3** = no event bus; **4** = timeout (check `docker logs kirp-agent-processor`).

**Webhooks (Slack / WhatsApp):** tenant routing uses env only — set `SLACK_WEBHOOK_TENANT_ID` / `SLACK_WEBHOOK_SPACE_ID` / `SLACK_WEBHOOK_USER_ID` and `WHATSAPP_WEBHOOK_*` (see `src/api/v1_ingestion.py`). The JSON body cannot choose a tenant.

## 5. Health & smoke

- **Health (API):** `GET http://localhost:8080/health`  
  Example: `curl -sS http://localhost:8080/health`  
  Expect `"status":"healthy"` when stores are up (not `/api/v1/health` — that path is not the app health check).

**Terminal tip:** run `curl` on its **own line**. If you paste Hebrew text (e.g. “ו־”) before `curl`, the shell looks for a command named `ו־curl` → `command not found`. Without `curl` installed, use:  
`docker compose -f deploy/docker-compose.prod.yml exec kirp-api curl -sS http://127.0.0.1:8000/health`

### Dashboard auth (401 in browser)

The compose stack sets **`ENV=production`**, so the API expects a **JWT** unless you opt into dev mode:

| Approach | What to do |
|----------|------------|
| **A. Log in** | Email **`dev@localhost`**, password **`devdevdev`**. This user is seeded on API startup when Mongo is empty and seed succeeds. |
| **B. Skip JWT (local only)** | In **`.env.prod`**: `SKIP_AUTH=1`. In **`.env.local`** (Next): `NEXT_PUBLIC_SKIP_AUTH=1` and `NEXT_PUBLIC_API_URL=http://localhost:8080`. Restart API and `npm run dev`. |

Use **B** for fastest UI work; use **A** to test real login.
- **Smoke script:** `./deploy/smoke-test.sh` — health + onboarding + Stripe webhook signature check.

---

## 6. Troubleshooting

```bash
docker compose -f deploy/docker-compose.prod.yml ps
docker compose -f deploy/docker-compose.prod.yml logs kirp-api --tail 120
```

**Do not run `docker volume prune -f` blindly.** It deletes **all** unused volumes on your machine (other projects too), not only KIRP. Prefer `docker compose -f deploy/docker-compose.prod.yml down -v` when you intend to reset **this** stack only.

**Mongo / `mongosh`:** run it **inside** the container, and give Mongo a few seconds after `up` before pinging:

```bash
docker compose -f deploy/docker-compose.prod.yml exec mongo mongosh --eval 'db.adminCommand({ ping: 1 })'
```

If you see `ECONNREFUSED 127.0.0.1:27017` immediately after start, wait ~5s and retry (race on first boot).

---

## 7. Related docs

- **Daily revenue dry-run (~5 min):** [`deploy/DAILY_CHECKLIST.md`](DAILY_CHECKLIST.md)
- Architecture: [`UNIFIED_ARCHITECTURE.md`](../UNIFIED_ARCHITECTURE.md)
- Doc index: [`docs/README.md`](../docs/README.md)
- Incident / revenue one-pagers: `deploy/INCIDENT_RUNBOOK.md`, `deploy/SAAS_REVENUE_GUIDE.md`, `deploy/VELOCITY.md` (to be merged/slimmed over time)
