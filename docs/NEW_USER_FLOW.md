# New user — one path from zero to value

Use this for the first **3 users** without a long handover.

## 1. Sign up

- Open the app **`/signup`**, enter name, email, password.
- You get a **tenant**, **user**, and **trial** automatically.

## 2. First action — ingest (one of two ways)

### A) Dashboard (fastest)

- Open **`/dashboard`**.
- If you see **“No events yet”**, click **Run first test ingest**.
- Or type anything under **“הוסף ידע או משימה”** and click **הוסף**.

### B) Copy-paste API (needs a login token)

After login, the browser stores `access_token`. Example:

```bash
export API=http://localhost:8000
export TOKEN='paste_access_token_here'

curl -sS -X POST "$API/api/v1/ingest" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"Hello KIRP — first event from curl.","source":"curl_first_run"}'
```

Tenant / user / space come from the JWT (body `tenant_id` is not used for routing).

## 3. See the result

- **`/dashboard`** → **Recent activity** should list the new event (after refresh / reload).
- **Plan & usage** shows **trial** or **active**, **pipeline runs**, and a link to **Billing**.

## 4. Billing (when ready)

- Open **`/billing`** → **Upgrade** / Checkout (Stripe test or live, per environment).
- Full payment E2E checklist: **`docs/SAAS_E2E_PAYMENT.md`** and **`scripts/verify-saas-e2e.sh`**.
