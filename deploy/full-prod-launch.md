# Full Production Launch Guide (KIRP SaaS)

This is the final operator runbook for launching KIRP SaaS in production.

## 1) Prerequisites

- Windows with Docker Desktop installed.
- WSL distro configured and project checked out.
- Docker Desktop WSL integration enabled for your distro.

### Enable Docker in WSL

1. Docker Desktop -> **Settings** -> **Resources** -> **WSL Integration**
2. Toggle your distro to **ON**
3. **Apply & Restart**
4. Restart terminal and verify:

```bash
docker --version
docker compose version
```

---

## 2) Production env file

Start from example:

```bash
cp deploy/.env.prod.example .env.prod
```

Set real production values:

- `STRIPE_SECRET_KEY` = live Stripe secret
- `STRIPE_PRICE_ID` = live subscription price id
- `STRIPE_WEBHOOK_SECRET` = live webhook signing secret
- `DATABASE_URL` = production Postgres connection
- `REDIS_URL` = production Redis connection
- `FRONTEND_URL` = production dashboard domain
- `ONBOARDING_RL_MAX=5`

Fail-fast startup is enabled in production mode. Missing required values stop boot immediately.

---

## 3) One-command launch

```bash
./deploy/launch-prod.sh
```

What it runs:

1. Copies `deploy/.env.prod.example` -> `.env.prod` (if you let it)
2. `docker compose -f deploy/docker-compose.prod.yml up -d --build`
3. `./deploy/smoke-test.sh`

---

## 4) Expected smoke output template

```text
Copied deploy/.env.prod.example -> .env.prod
[+] Running ...
Waiting for API health...
health: 200
{"status":"healthy","event_store":"ok","rag_engine":"ok"}
onboarding: 201
{"tenant_id":"<uuid>","tenant_name":"acme-smoke-<ts>","lifecycle":"trial",...}
stripe_webhook: 200
{"received":true}
SMOKE_OK: health=200 onboarding=201 webhook=200
```

---

## 5) Manual verification

```bash
curl -sS http://localhost:8080/health
curl -sS -X POST http://localhost:8080/api/v1/onboarding \
  -H 'Content-Type: application/json' \
  -d '{"tenant_name":"acme","email":"user@acme.com"}'
```

Expected:
- Health returns healthy JSON
- Onboarding returns tenant + trial + API keys

---

## 6) Go-live checklist

- [x] Stripe webhook and checkout endpoints deployed
- [x] Tenant lifecycle states wired (`trial`/`active`/`suspended`)
- [x] API key auth (`Authorization: Kirp <secret_key>`)
- [x] Billing dashboard and usage details route live
- [x] Production fail-fast env validation enabled
- [x] Production compose + smoke script committed
- [x] Launch runbook complete

KIRP SaaS launch guide status: **READY**.
