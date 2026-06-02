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
2. Open **`http://localhost:3000/billing`** — no dashboard login required for dry-run (AppShell allows this route for API-key flow).
3. **One-click dry-run:** use *Create tenant & load billing* (calls `POST /api/v1/onboarding`, stores `kirp_sk_…`, loads usage with `Authorization: Kirp`).
4. Or paste **tenant UUID + secret** under *Already have onboarding response?*

**Auth priority on this page:** if a Kirp secret is stored (session/local), it is used for API calls; otherwise **Bearer** from dashboard login. Clear stored key to use JWT only.

**Stripe redirect:** checkout uses your current browser origin for success/cancel URLs (so port 3000 works without changing `FRONTEND_URL` on the API).

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

## 5b. Dashboard user + JWT (one command)

After the stack is up (no rebuild):

```bash
./deploy/local-dashboard-verify.sh
```

Prints email + password to use on `http://localhost:3100/login`, and checks `signup` → `me` → `stats`.

---

## Week 7 focus

| Step | Success signal |
|------|----------------|
| Compose up | `/health` 200 |
| Onboarding | 201 + `secret_key` |
| Usage (curl) | 200 + breakdown JSON |
| Billing UI | Upgrade visible when logged in + `NEXT_PUBLIC_API_URL` correct |
| Webhook | 200 + lifecycle updated in DB / usage views |
