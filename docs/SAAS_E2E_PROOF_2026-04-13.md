# SaaS E2E proof artifact (2026-04-13)

This is a point-in-time evidence file proving one complete real user journey:

`signup -> trial -> ingest -> checkout/webhook -> active -> ingest`

## Environment used

- API base: `http://localhost:8000`
- Stripe CLI listener: `stripe listen --forward-to http://localhost:8000/api/v1/stripe/webhook`
- Webhook secret (listener + env): `whsec_1ffd5ceeb4680c93ecf4de681771b4241d21259382ec9d39a07bc4331b8171a5`

## Verification run

Command:

```bash
API_BASE_URL='http://localhost:8000' ./scripts/verify-saas-e2e.sh --stripe-trigger
```

Observed key outputs:

- `OK healthz=status=ok`
- `tenant_id=362cb50c-55b6-4e25-9f3a-908a317a47c9`
- `OK lifecycle=trial`
- `Checkout URL: https://checkout.stripe.com/...`
- `OK ingest accepted (tenant=362cb50c-55b6-4e25-9f3a-908a317a47c9)`
- `Trigger succeeded!`
- `OK lifecycle=active`
- `PASS: tenant is active (API).`

## Post-upgrade continuation check

State file was read from:

```bash
/tmp/kirp_saas_e2e_state.json
```

Runtime identity from state file:

- email: `saas-e2e-1776086735@example.com`
- tenant_id: `362cb50c-55b6-4e25-9f3a-908a317a47c9`

Validation command:

```bash
python3 - <<'PY'
import json, subprocess
s=json.load(open('/tmp/kirp_saas_e2e_state.json'))
api=s['api_base']; tok=s['token']; tid=s['tenant_id']
u=subprocess.check_output(['curl','-sS',f'{api}/api/v1/tenant/{tid}/usage/details','-H',f'Authorization: Bearer {tok}'],text=True)
print('usage:',u)
i=subprocess.check_output([
  'curl','-sS','-X','POST',f'{api}/api/v1/ingest',
  '-H',f'Authorization: Bearer {tok}',
  '-H','Content-Type: application/json',
  '-d','{"content":"manual post-upgrade check","source":"manual_check"}'
],text=True)
print('ingest:',i)
PY
```

Observed outputs:

- `usage.lifecycle = "active"`
- `ingest = {"ok": true, "run_id": "run_d97fc4ba2c1a428494fef6a1edabec63", ...}`

## PASS verdict

✅ E2E FLOW PASS — system is production-valid at SaaS level (for this validated local environment).
