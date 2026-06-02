# Engineering command model

Operating doctrine: **how this organization runs platform engineering** so architectural truth does not decay into narrative, and **false confidence** is treated as a failure mode.

---

## 1. How reviews happen

1. **Truth sources rank:** running code + deploy configs > automated tests > `docs/RUNTIME_*` + `RISK_REGISTER.md` > marketing or roadmap prose.  
2. **Staff review triggers:** any change to auth, tenant context, event bus, governance, execute/webhooks, or persistence filters → **mandatory** `AUTHORIZATION_BOUNDARY_AUDIT.md` delta or attached matrix.  
3. **No silent “LGTM”** on security surfaces: reviewer states **SAFE / PARTIAL / DANGEROUS** for touched routes.  
4. **Documents that lie are defects:** README/compose drift is a **P1** process bug until fixed.

---

## 2. How risks are escalated

| Severity | Action |
| -------- | ------ |
| **P0** | Stop merge; incident channel; executive visibility if prod-adjacent |
| **P1** | Block release for affected surface; ticket with owner + ETA |
| **P2** | Scheduled sprint debt |
| **P3** | Backlog |

**Escalation rule:** **Cross-tenant integrity or confidentiality** is always **P0** until mitigated—no downgrade without written technical disproof.

---

## 3. How production approval works

1. **`PRODUCTION_GATES.md`** must be **PASS** or **waived** per gate.  
2. **`RISK_REGISTER.md`** must have no open **P0** for the release blast radius, or waivers on file.  
3. **Verification:** subset of `VERIFICATION_STRATEGY.md` linked in release checklist with **artifact links** (CI run, report).  
4. **Rollback:** one-step revert or feature flag position documented before ship.

**Who approves:** named engineer + (if policy) security. **UNASSIGNED** owner is **not** approvable.

---

## 4. How operational signoff works

- On-call acknowledges: **runbooks** for Kafka down, Redis down, OPA down, poison message (see `CHAOS_AND_RECOVERY.md`).  
- **SLOs:** lag thresholds for Kafka consumer; Redis memory; OPA latency—**numeric**, not “healthy.”

---

## 5. How incidents are reviewed

1. **Timeline first:** `trace_id`, `run_id`, `event_id`, Kafka offset if available.  
2. **Classify:** tenant leak vs replay vs auth bypass vs infra.  
3. **Output:** new or updated risk row; new **production gate** if warranted; regression test within **7 days** for P0/P1.  
4. **Blameless** on humans; **ruthless** on missing gates.

---

## 6. How failures become safeguards

| Failure class | Safeguard |
| ------------- | --------- |
| IDOR | Tenant-scoped DB primitive + CI grep |
| False 2xx | Contract tests + synthetic broker outage |
| Poison | DLQ automation + alert |
| Doc drift | Compose/README check job or link to `RUNTIME_REALITY_MATRIX` only |

---

## 7. How architectural truth is maintained

- **Single risk registry:** `RISK_REGISTER.md` (this wave). **Closure** = row moves to “resolved” with PR link + test link—not deleted.  
- **Quarterly:** re-run authorization audit grep; refresh `RUNTIME_GUARANTEES.md` UNVERIFIED section.  
- **Principle:** **Visible risk beats hidden risk.** Optimism without proof is a process violation.

---

## 8. Anti-patterns (non-negotiable)

- “We’ll fix auth later” on a route that is already public.  
- Waivers without compensating controls.  
- Dismissing UUID guessing as “unlikely” **without** rate limits and monitoring.  
- Renaming **DANGEROUS** to “tech debt” in reviews.

---

## 9. Relation to prior artifacts

| Artifact | Role |
| -------- | ---- |
| `SKEPTICAL_STAFF_REVIEW.md` | Opinionated gate narrative |
| `PRODUCTION_GATES.md` | Binary release rules |
| `RISK_REGISTER.md` | Inventory + ownership |
| `REMEDIATION_PLAN.md` | How to close |

This model **does not replace** code review; it **binds** code review to operational outcomes.
