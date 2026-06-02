# Production gates

Hard rules: **if a gate fails, production release is blocked** until waived with a **written compensating control** signed by engineering + security (not self-waived).

---

## Current blockers (as of this register)

These reflect **known defects** in repository behavior or verification, not opinions.

| Gate ID | Condition | Evidence basis |
| ------- | --------- | -------------- |
| PG-01 | No cross-tenant **mutation** by resource id without JWT tenant match | R-001, R-006, R-012 |
| PG-02 | No cross-tenant **read** of graph nodes or DLQ payloads by id without tenant match | R-005, R-007 |
| PG-03 | No **client-trusted** `tenant_id` on externally reachable execute endpoints without explicit gateway auth proof | R-006 |
| PG-04 | Redis processor idempotency keys are **tenant-namespaced** OR documented waiver with dual-check rollout complete | R-003 |
| PG-05 | Webhook paths do not return **2xx success** when Kafka publish failed, OR waiver: webhooks not in SoR and lag alerting mandatory | R-004 |

**Status:** **FAIL** on PG-01–PG-05 for public multi-tenant SaaS until remediations in `REMEDIATION_PLAN.md` ship.

---

## Near-term blockers (block regulated / high-scale, not all MVPs)

| Gate ID | Condition |
| ------- | --------- |
| PG-10 | Production `ENV` without `OPA_URL` must not silently mean “no policy” **unless** `ALLOW_GOVERNANCE_FAIL_OPEN` explicitly set and logged at startup |
| PG-11 | Poison message policy documented and automated (DLQ or skip+alert) |
| PG-12 | Request correlation ID on all mutating responses **or** waiver with log aggregator rule set |

---

## Acceptable operational debt (explicit, time-bounded)

| Debt ID | Description | Waiver condition |
| ------- | ----------- | ------------------ |
| OD-01 | Kafka ordering not per-tenant | Documented SLO: ordering not required for product |
| OD-02 | `count_events` optional tenant at primitive level | No public route calls without tenant; CI grep |
| OD-03 | Single-topic Kafka | ACLs + private network; producer allowlist |

---

## Gate evaluation cadence

- **Pre-merge:** CI unit + integration subset tied to touched risks (see `VERIFICATION_STRATEGY.md`).  
- **Pre-release:** Full gate table sign-off.  
- **Post-incident:** Any incident touching tenant or replay adds a **new gate** or tightens an existing one.

---

## Waivers

Waivers live only in `docs/` as a dated addendum listing: risk ID, approver, expiry date, compensating control. **Absent waiver document = no waiver.**
