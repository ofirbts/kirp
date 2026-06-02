# KIRP docs — navigation

Use this file as the **map**. Deep design lives in linked files; avoid duplicating architecture prose here.

## Sources of truth (3)

| What | File |
|------|------|
| Architecture & principles | [`UNIFIED_ARCHITECTURE.md`](../UNIFIED_ARCHITECTURE.md) (repo root) |
| How to run the prod-style stack locally | [`deploy/README.md`](../deploy/README.md) |
| This map + where to look next | **this file** |

## Runtime truth (ops + staff review)

| What | File |
|------|------|
| Subsystems vs code vs compose | [`RUNTIME_REALITY_MATRIX.md`](RUNTIME_REALITY_MATRIX.md) |
| Failure modes (actual behavior) | [`FAILURE_SEMANTICS.md`](FAILURE_SEMANTICS.md) |
| Diagram → module traceability | [`ARCHITECTURE_TRACEABILITY.md`](ARCHITECTURE_TRACEABILITY.md) |
| Observability / audit / gaps | [`OPERATIONAL_CONFIDENCE.md`](OPERATIONAL_CONFIDENCE.md) |
| Readiness verdict + scores | [`PRODUCTION_READINESS_REVIEW.md`](PRODUCTION_READINESS_REVIEW.md) |
| Delivery / idempotency / retry matrix | [`RUNTIME_GUARANTEES.md`](RUNTIME_GUARANTEES.md) |
| Tenant isolation & leakage risks | [`TENANT_ISOLATION_REVIEW.md`](TENANT_ISOLATION_REVIEW.md) |
| Replay & side-effect classification | [`SIDE_EFFECT_AND_REPLAY_SAFETY.md`](SIDE_EFFECT_AND_REPLAY_SAFETY.md) |
| Logs / metrics / operator questions | [`OBSERVABILITY_REVIEW.md`](OBSERVABILITY_REVIEW.md) |
| Chaos, recovery, poison messages | [`CHAOS_AND_RECOVERY.md`](CHAOS_AND_RECOVERY.md) |
| Skeptical production approval lens | [`SKEPTICAL_STAFF_REVIEW.md`](SKEPTICAL_STAFF_REVIEW.md) |
| Risk registry (closure) | [`RISK_REGISTER.md`](RISK_REGISTER.md) |
| Authorization boundary audit | [`AUTHORIZATION_BOUNDARY_AUDIT.md`](AUTHORIZATION_BOUNDARY_AUDIT.md) |
| P0/P1 remediation plan (strategy only) | [`REMEDIATION_PLAN.md`](REMEDIATION_PLAN.md) |
| Verification strategy | [`VERIFICATION_STRATEGY.md`](VERIFICATION_STRATEGY.md) |
| Production release gates | [`PRODUCTION_GATES.md`](PRODUCTION_GATES.md) |
| Engineering command model | [`ENGINEERING_COMMAND_MODEL.md`](ENGINEERING_COMMAND_MODEL.md) |

## First reads for developers

| Topic | Doc |
|-------|-----|
| Quick start | [`QUICKSTART.md`](QUICKSTART.md) |
| Env & tokens (API vs UI) | [`ENV_AND_UI_TOKENS.md`](ENV_AND_UI_TOKENS.md), [`env.local.example`](env.local.example) |
| Events | [`EVENTS.md`](EVENTS.md) |
| Production checklist | [`production_checklist.md`](production_checklist.md) |
| Daily revenue / stack dry-run (~5 min) | [`deploy/DAILY_CHECKLIST.md`](../deploy/DAILY_CHECKLIST.md) |
| Repo hygiene & doc strategy | [`REPO_AND_CURSOR_HYGIENE_PLAN.md`](REPO_AND_CURSOR_HYGIENE_PLAN.md) |

## Architecture & planning (deeper)

- [`KIRP_ARCHITECTURE.md`](KIRP_ARCHITECTURE.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) — if both exist, treat **`UNIFIED_ARCHITECTURE.md`** as the tie-breaker for “current intent”.
- Roadmaps / vision: [`ROADMAP_TO_100.md`](ROADMAP_TO_100.md), [`KIRP_MASTER_PLAN.md`](KIRP_MASTER_PLAN.md), [`VISION_AND_UI.md`](VISION_AND_UI.md), and related files in this folder.

## UI & verification

- Router structure: [`APP_ROUTER_STRUCTURE.md`](APP_ROUTER_STRUCTURE.md)
- UI deployment: [`UI_DEPLOYMENT.md`](UI_DEPLOYMENT.md)
- E2E / validation: [`E2E_VERIFICATION_CHECKLIST.md`](E2E_VERIFICATION_CHECKLIST.md), [`VALIDATE_UI.md`](VALIDATE_UI.md)
- SaaS: new-user path [`NEW_USER_FLOW.md`](NEW_USER_FLOW.md); Stripe E2E runbook [`SAAS_E2E_PAYMENT.md`](SAAS_E2E_PAYMENT.md), script [`../scripts/verify-saas-e2e.sh`](../scripts/verify-saas-e2e.sh), proof [`SAAS_E2E_PROOF_2026-04-13.md`](SAAS_E2E_PROOF_2026-04-13.md); trace runbook [`TRACE_VERIFICATION.md`](TRACE_VERIFICATION.md)

## Audits & reports (historical context)

Files matching `*AUDIT*`, `*REPORT*`, `*VERIFICATION*`, `*SUMMARY*` are usually **point-in-time**. Prefer them for “why we decided X”; for **current behavior**, trust code + `UNIFIED_ARCHITECTURE.md` + tests.

## Duplicates & cleanup log

- [`DUPLICATES_AND_CLEANUP.md`](DUPLICATES_AND_CLEANUP.md) — what was already deduplicated; use before deleting anything ambiguous.
