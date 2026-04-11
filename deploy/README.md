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

## 5. Health & smoke

- **Health (API):** `GET http://localhost:8080/health`  
  Example: `curl -sS http://localhost:8080/health`  
  Expect `"status":"healthy"` when stores are up (not `/api/v1/health` — that path is not the app health check).
- **Smoke script:** `./deploy/smoke-test.sh` — health + onboarding + Stripe webhook signature check.

---

## 6. Troubleshooting

```bash
docker compose -f deploy/docker-compose.prod.yml ps
docker compose -f deploy/docker-compose.prod.yml logs kirp-api --tail 120
```

---

## 7. Related docs

- Architecture: [`UNIFIED_ARCHITECTURE.md`](../UNIFIED_ARCHITECTURE.md)
- Doc index: [`docs/README.md`](../docs/README.md)
- Incident / revenue one-pagers: `deploy/INCIDENT_RUNBOOK.md`, `deploy/SAAS_REVENUE_GUIDE.md`, `deploy/VELOCITY.md` (to be merged/slimmed over time)
