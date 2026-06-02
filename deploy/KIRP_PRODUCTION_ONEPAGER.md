# KIRP Production System — Ready for $10K MRR

**What it is:** Multi-tenant enterprise AI platform — event-sourced ingest, RAG, agents, M3 IdentityOS, governance (OPA), and a Next.js operator dashboard.

**Why it supports early revenue ($10K MRR):** Tenant isolation, run-level observability, LLM cost quotas, and production alerting are implemented in code paths customers touch (API + workers + UI), not slideware.

---

## Customer-facing capabilities

| Capability | Delivery |
|------------|----------|
| **Secure multi-tenancy** | JWT context; Redis `tenant:{id}:…`; run hashes `tenant:{tenant_id}:{run_id}` + `run_lookup`. |
| **Predictable ingest** | Kafka + `EventPipeline.run`; optional **`PIPELINE_RUN_POLICY=strict`** for deterministic failures. |
| **Operator visibility** | Run monitor (`/monitoring`), run status API, tenant runs + SSE, **`model`** on timeline. |
| **Cost control** | Per-tenant LLM USD counter, **`/usage`**, **429** on quota exceed. |
| **Incident signals** | Hourly failure / rate alerts, **`/alerts`**, Slack hook optional, dashboard badges. |

---

## Technical proof points (ship with sales engineering)

1. **100% `EventPipeline.run` lifecycle coverage** — all call sites create or inherit RunController state before work runs.
2. **Grafana** — import `deploy/grafana/kirp_pipeline_dashboard.json`; scrape `/observability/metrics/prometheus`.
3. **Reconciliation** — Celery beat repairs partial runs (history + projections) on a 15-minute cadence.

**Deep runbook (matrices, env semantics, doc-linked tests):** repo root **`SYSTEM_STATUS.md`**.

---

## What you still do in the real world (not in repo)

- TLS, secrets management, backup/restore drill, SLOs on your cluster.
- Stripe / billing UI (Week 6 option **C**).
- K8s HPA / multi-region (Week 6 option **B**).

---

## One-line pitch

**KIRP is a production-grade, tenant-safe AI operations core — ingest to insight with enforced run lifecycle, quotas, and alerts — ready to price and onboard paying teams.**

---

*Internal doc — align with `SYSTEM_STATUS.md` and `CHANGELOG.md`.*
