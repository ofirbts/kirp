# KIRP — Daily revenue flow (~5 min)

**Purpose:** Prove the stack and the SaaS path (health → tenant → usage → billing intent → Stripe signals) without opening new doc rabbit holes.

**API base (Docker prod compose):** `http://localhost:8080`  
**Billing UI (Next.js — not on 8080):** `http://localhost:3000/billing` (after `npm run dev` in repo root)

---

## 0. One-time / env

- Root **`.env.prod`**: `STRIPE_*`, `DATABASE_URL`, `REDIS_URL`, and **`MONGO_URI=mongodb://mongo:27017/kirp`** (inside Docker — not `localhost`).
- **Dashboard → API:** in `.env.local`, set `NEXT_PUBLIC_API_URL=http://localhost:8080` so the billing page hits the same API as Docker.

**Warning:** `./deploy/launch-prod.sh` **overwrites** `.env.prod` from the example. Prefer:

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
./deploy/smoke-test.sh
```

when you already have a filled `.env.prod`.

---

## 1. Stack

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
curl -sS http://localhost:8080/health
```

Expect HTTP **200** and JSON with `"status":"healthy"` (and stores ok when Mongo/Postgres are reachable).

---

## 2. Customer journey (API)

**Onboarding** (no auth):

```bash
curl -sS -X POST http://localhost:8080/api/v1/onboarding \
  -H "Content-Type: application/json" \
  -d '{"tenant_name":"acme-daily-'$(date +%s)'","email":"test@test.com"}'
```

Save from the JSON:

- `tenant_id` (UUID)
- `secret_key` (`kirp_sk_...`)

**Usage breakdown** (auth = **Kirp secret**, path = **same `tenant_id`**):

```bash
export TENANT_ID='<paste tenant_id UUID>'
export KIRP_SECRET='<paste secret_key>'

curl -sS "http://localhost:8080/api/v1/tenant/${TENANT_ID}/usage/details" \
  -H "Authorization: Kirp ${KIRP_SECRET}"
```

Note: `Authorization: Kirp <secret>` (space after `Kirp`). The path accepts UUID or tenant **name**, but `ctx.tenant_id` must match the key’s tenant — use the UUID from onboarding for dry-runs.

---

## 3. Billing UI (upgrade button)

1. `npm run dev` (default `http://localhost:3000`).
2. Open:  
   `http://localhost:3000/billing?tenant=<TENANT_ID>`

**Today’s behavior:** the page calls the API with **Bearer** tokens from the dashboard session (`localStorage`), not with the onboarding `kirp_sk_` key. So:

- If you are **logged in** as a user for that tenant, you should see usage + **Upgrade with Stripe** (needs `STRIPE_PRICE_ID` on the API).
- For a **cold “API-only” customer**, use the **curl** usage call above until the UI supports `Kirp` or a dev token path.

---

## 4. Stripe webhooks (lifecycle)

Signed POST to the API (same shape as `deploy/smoke-test.sh`):

- `customer.subscription.created` → tenant moves toward **active** (when `metadata.tenant_id` matches).
- `customer.subscription.deleted` → **suspended** / billing terminal state per `stripe_service`.

Use the **Stripe signing secret** (`STRIPE_WEBHOOK_SECRET`) and raw JSON body; see `smoke-test.sh` for a working HMAC example.

---

## 5. Quick regression (optional)

```bash
./deploy/smoke-test.sh
```

Expect: `SMOKE_OK: health=200 onboarding=201 webhook=200`.

---

## Week 7 focus

| Step | Success signal |
|------|----------------|
| Compose up | `/health` 200 |
| Onboarding | 201 + `secret_key` |
| Usage (curl) | 200 + breakdown JSON |
| Billing UI | Upgrade visible when logged in + `NEXT_PUBLIC_API_URL` correct |
| Webhook | 200 + lifecycle updated in DB / usage views |
