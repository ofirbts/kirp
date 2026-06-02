# SaaS Launch Checklist (Final Gate)

Status date: 2026-04-10
Scope: Stripe billing, onboarding, tenant lifecycle, auth, production runtime safety.

## 1) Billing and keys
- [x] Stripe production secret configured (`STRIPE_SECRET_KEY`)
- [x] Stripe subscription price configured (`STRIPE_PRICE_ID`)
- [x] Stripe webhook secret configured (`STRIPE_WEBHOOK_SECRET`)
- [x] PaymentIntent path configured for dashboard checkout (`/api/v1/stripe/create-payment-intent`)

## 2) Domains and CORS
- [x] `FRONTEND_URL` set to production domain
- [x] API `CORS_ORIGINS` includes production frontend domain(s)
- [x] Billing/upgrade redirects point to production billing route

## 3) Rate limits and abuse protection
- [x] Onboarding limit configured (`ONBOARDING_RL_MAX=5`, `ONBOARDING_RL_WINDOW_SEC=60`)
- [x] API global limit policy configured (`API_RL=100/min`) via ingress/API gateway
- [x] Stripe/public endpoints reviewed for per-IP controls

## 4) Data and indexing
- [x] Postgres index on tenant lookup key (`tenants.name`) validated
- [x] Lifecycle JSON path indexed for ops queries (`tenants.extra->>'lifecycle'`) if needed at scale
- [x] Tenant secret hash persistence verified (`tenants.extra.secret_key_hash`)

## 5) Observability and alerting
- [x] Prometheus scraping `/observability/metrics/prometheus`
- [x] Grafana dashboards imported (`deploy/grafana/kirp_pipeline_dashboard.json`)
- [x] Alerts wired for pipeline anomalies (`kirp_pipeline_*`)
- [x] Quota and billing-related alert rules reviewed (`quota_exceeded`, tenant suspension/trial expiry)

## 6) Runtime safety
- [x] Required env validation enabled at startup (Stripe/DB/Redis)
- [x] Non-production defaults removed from production env files
- [x] Secrets injected from secure store (not committed files)

## 7) End-to-end launch checks
- [x] Onboarding flow: create tenant -> trial lifecycle -> keys issued once
- [x] Stripe checkout flow: create checkout session -> webhook updates lifecycle
- [x] API key auth flow: `Authorization: Kirp <secret>` accepted/rejected correctly
- [x] Billing dashboard: usage details + upgrade CTA + trial/suspended states visible

## 8) Go-live command checklist
- [x] `docker compose -f deploy/docker-compose.prod.yml up -d`
- [x] `curl http://localhost:8000/health` returns healthy
- [x] `curl -X POST /api/v1/onboarding` returns tenant + keys + `lifecycle=trial`
- [x] `POST /api/v1/stripe/webhook` updates tenant lifecycle

## Launch Decision
- [x] Ready for staged production launch
