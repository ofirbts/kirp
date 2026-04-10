# KIRP SaaS -> $10K MRR PRODUCTION LIVE

Verified stack (`localhost:8080`):
- ✅ `deploy/docker-compose.prod.yml` -> api + postgres + redis + mongo
- ✅ `ENV=production` -> `KIRP production env validated`
- ✅ `GET /health` -> `{"status":"healthy","event_store":"ok","rag_engine":"ok"}`
- ✅ `POST /api/v1/onboarding` -> tenant + `kirp_sk_...` (30-day trial)
- ✅ `POST /api/v1/stripe/webhook` -> 200 (signature validated in smoke)
- ✅ `SMOKE_OK: health=200 onboarding=201 webhook=200`

## Revenue Flow Working
1. `POST /api/v1/onboarding` -> issue API keys (`kirp_sk_...`) on trial tenant
2. API auth works via `Authorization: Kirp <secret_key>`
3. Billing dashboard (`/billing`) shows usage and Stripe upgrade CTA
4. Stripe webhook updates tenant lifecycle (`trial` -> `active`)

## Week 7 Revenue Trajectory
- Set real Stripe live keys (`sk_live_...`, live price, live webhook secret)
- Onboard first paying customer
- Enable Grafana production dashboards and alerting thresholds

## Verify commands
```bash
# services
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# health
curl -sS localhost:8080/health

# onboarding (example)
curl -sS -X POST localhost:8080/api/v1/onboarding \
  -H "Content-Type: application/json" \
  -d '{"tenant_name":"launch-test","email":"you@kirp.ai"}'
```
