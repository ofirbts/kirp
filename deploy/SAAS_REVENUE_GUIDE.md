# KIRP SaaS Revenue -> $10K MRR

## Launch (30s)
```bash
cd deploy && ./launch-prod.sh
```

## Customer Journey
1. `POST /api/v1/onboarding` -> `kirp_sk_...` (trial)
2. `http://localhost:8080/billing` -> usage chart + quota visibility
3. Click **Upgrade** -> Stripe Checkout
4. Stripe webhook -> tenant `lifecycle=active`
5. Full API usage -> revenue tracked

Status: **Ready**
