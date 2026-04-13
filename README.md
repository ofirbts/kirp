# KIRP - Enterprise AI SaaS

## SaaS onboarding & payments

- **New users (signup → first ingest → billing):** [docs/NEW_USER_FLOW.md](docs/NEW_USER_FLOW.md)
- **E2E payment runbook:** [docs/SAAS_E2E_PAYMENT.md](docs/SAAS_E2E_PAYMENT.md) · run `./scripts/verify-saas-e2e.sh` (see doc for `stripe listen`).
- **E2E proof artifact (PASS 2026-04-13):** [docs/SAAS_E2E_PROOF_2026-04-13.md](docs/SAAS_E2E_PROOF_2026-04-13.md)

## Start
```bash
cd deploy && ./launch-prod.sh
curl localhost:8080/health
```

## Revenue
`POST /onboarding` -> keys -> `/billing` -> Stripe -> $$$

Status: **$10K MRR Launch Ready**
