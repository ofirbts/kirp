# SaaS E2E — signup through Stripe payment (test mode)

This is the **single reference path** to prove: signup → trial → Billing → Checkout Session → webhook → `lifecycle: active`, verified on the API (and manually on the dashboard).

## Prerequisites

- API running with **Postgres** (tenant rows persist).
- **Do not rely on `SKIP_AUTH=1`** for this flow; the script uses a real JWT.
- Stripe **test** keys on the API process:
  - `STRIPE_SECRET_KEY`
  - `STRIPE_PRICE_ID` (recurring price for Checkout subscription mode)
  - `STRIPE_WEBHOOK_SECRET` — must match the secret shown by Stripe CLI when forwarding (starts with `whsec_`).

## Terminal A — Stripe → your API

Forward webhooks to the local API (or your staging URL):

```bash
stripe listen --forward-to http://localhost:8000/api/v1/stripe/webhook
```

Copy the **`whsec_...`** value into `STRIPE_WEBHOOK_SECRET` and **restart the API** so signature verification passes.

## Terminal B — automated steps + browser checkout

```bash
export API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
./scripts/verify-saas-e2e.sh
```

The script will:

1. `POST /api/v1/auth/signup` → tenant + user + **trial**
2. `GET /api/v1/tenant/{id}/usage/details` → assert **`lifecycle` is `trial`**
3. `POST /api/v1/tenant/{id}/stripe/checkout-session` → print **Checkout URL**
4. Wait for you to **finish Checkout in the browser** (test card `4242 4242 4242 4242`, any future expiry, any CVC)
5. Poll usage until **`lifecycle` is `active`** or timeout

### Proof checklist

| Step | Check |
|------|--------|
| API after signup | `GET .../usage/details` → `lifecycle: "trial"` |
| After successful payment | Same endpoint → `lifecycle: "active"` |
| Dashboard | Open `/dashboard` → **Plan & usage** shows **active** (not trial) |

## Automation without a browser (same webhook code path)

If the [Stripe CLI](https://stripe.com/docs/stripe-cli) is installed and **`stripe listen`** is running (Terminal A) with `STRIPE_WEBHOOK_SECRET` aligned:

```bash
./scripts/verify-saas-e2e.sh --stripe-trigger
```

This runs `stripe trigger customer.subscription.created` with `subscription:metadata.tenant_id=<your tenant UUID>`, then polls until `active`. It **does not** click through Checkout UI; it proves the **webhook + lifecycle update** end-to-end. Use the default script (no flag) to prove **Checkout Session + payment** as well.

## Troubleshooting

- **503 on checkout-session** — `STRIPE_SECRET_KEY` or `STRIPE_PRICE_ID` missing on the server.
- **400 on webhook** — `STRIPE_WEBHOOK_SECRET` does not match the `stripe listen` secret.
- **Lifecycle stays `trial` after payment** — webhook not received; confirm Terminal A is running and URL is reachable.
