# KIRP Governance Policy — Structure and Alignment

## יעילות ובטיחות (Efficiency & safety)

- **Space:** `all` ו־`default` מאוחדים לכלל אחד: `input.space_id in ["all", "default"]`.
- **roles / space_members:** שימוש ב־`some x in input.roles` / `some m in input.space_members` — אם מועבר string במקום מערך, אין התאמה (מניעת הרשאה שגויה).
- **ownership:** רק כאשר `input.resource_owner_id != ""` ו־מתאים ל־user_id (חסר או ריק = אין override).
- **space-admin:** נדרש `input.space_id != ""` (אין הרשאה כשמרחב לא מוגדר).
- **Allow:** אותו מספר כללים; reason ב־single complete rule עם סדר עדיפות ברור.

## Current layout (single file: `kirp.rego`)

Rules are grouped by responsibility:

1. **Tenant isolation** — `tenant_check`: same tenant or explicit cross-tenant grant.
2. **Space access** — `space_check`: private (owner), shared (member), org (admin/member).
3. **Overrides** — `ownership_allowed`, `role_allowed`: owner or privileged roles bypass space/risk.
4. **Risk model** — each risk component is a **single-valued** complete rule (e.g. `confidential_risk := 0.3 if { ... }` and `confidential_risk := 0 if { not ... }`) so `risk_score` is deterministic.
5. **Approval** — `requires_approval`: high risk, delete, confidential write, governance write.
6. **Allow** — read (tenant+space), write low-risk, write high-risk when approved, delete when approved, then ownership/role overrides.
7. **Reason** — **one** complete rule with **no default**; ordered `if / else` chain so exactly one output: allowed → tenant_mismatch → space_access_denied → high_risk_requires_approval → delete_requires_approval → approval_required → denied_by_policy.

## Why `reason` is fixed

Previously, `default reason := "denied_by_policy"` plus a rule that also set `reason` could lead to “complete rules must not produce multiple outputs” in Rego. The fix:

- Remove the default for `reason`.
- Define **only one** rule for `reason`, using an `if / else` chain so exactly one branch runs and assigns `r`.
- The last `else` sets `r := "denied_by_policy"`, so every evaluation gets a single reason.

## Optional split into modules

You can keep a single file or split for clarity and reuse:

| File          | Contents |
|---------------|----------|
| `tenant.rego` | `tenant_check` (and any future tenant helpers). |
| `space.rego`  | `space_check` (and any space helpers). |
| `risk.rego`   | All `*_risk` rules and `risk_score`. |
| `approval.rego` | `requires_approval`. |
| `decision.rego` | `allow` and `reason` (import tenant, space, risk, approval). |

- Each module would be in the same package `kirp.governance` so rules are composed by name.
- Entry point for the API would still be the same: e.g. `data.kirp.governance.allow`, `data.kirp.governance.reason`, `data.kirp.governance.risk_score`.
- OPA/bundle would include all `.rego` files under the policies directory.

## Alignment with SchemaEngine

- **tenant_id**: Every SchemaEngine call is scoped by `tenant_id`; governance enforces tenant isolation via `tenant_check`.
- **space_id**: List/get/tree/obligations accept `space_id` or `space_ids` (membership-aware); governance uses `space_check` for the requested space.
- **Ownership**: Policy uses `resource_owner_id` for overrides; schema layer does not currently store per-node “owner” — that can live in a separate table or in `extra` and be passed into Rego as `input.resource_owner_id`.
- **Roles**: Rego uses `input.roles` and `role_allowed`; the app should set `input.roles` from the auth/me or session so that tenant-admin / space-admin / governance-admin align with backend role checks.

No duplicate logic: Rego decides allow/deny and reason; the backend (and SchemaEngine) enforces tenant_id/space_id on every query so that data access matches the policy.
