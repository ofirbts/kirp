package kirp.governance

import rego.v1

#
# ============================================================
#  KIRP Governance Policy — Enterprise‑Grade Version
#  (Built on top of your existing logic, not replacing it)
# ============================================================
#

default allow := false
default requires_approval := false
default reason := "denied_by_policy"
default risk_score := 0
default role_allowed := false
default ownership_allowed := false

#
# ============================================================
# 1. Tenant Isolation (Hard Boundary)
# ============================================================
#
tenant_check if {
    input.tenant_id == input.user_tenant_id
}

# Cross‑tenant access only if explicitly granted
tenant_check if {
    input.tenant_id != input.user_tenant_id
    input.cross_tenant_grant == true
}

#
# ============================================================
# 2. Space‑Level Access Control
# ============================================================
#
space_check if {
    input.space_id == "private"
    input.user_id == input.space_owner_id
}

space_check if {
    input.space_id == "shared"
    input.user_id in input.space_members
}

space_check if {
    input.space_id == "org"
    input.user_role in ["admin", "member"]
}

#
# ============================================================
# 3. Ownership Rules
# ============================================================
#
ownership_allowed if {
    input.user_id == input.resource_owner_id
}

#
# ============================================================
# 4. Role‑Based Access Control (RBAC)
# ============================================================
#
role_allowed if {
    "tenant-admin" in input.roles
}

role_allowed if {
    "space-admin" in input.roles
    input.space_id != ""
}

role_allowed if {
    "governance-admin" in input.roles
}

#
# ============================================================
# 5. Risk Model (Your original logic — expanded)
# ============================================================
#
risk_score := score if {
    score := sum([
        confidential_risk,
        delete_risk,
        governance_risk,
        autonomy_risk,
        cross_tenant_risk,
        high_privilege_risk,
    ])
}

confidential_risk := 0
confidential_risk := 0.3 if input.sensitivity == "confidential"

delete_risk := 0
delete_risk := 0.4 if input.action == "delete"

governance_risk := 0
governance_risk := 0.2 if input.resource_type == "governance"

autonomy_risk := 0
autonomy_risk := 0.1 if input.agent_autonomy == "full"

cross_tenant_risk := 0
cross_tenant_risk := 0.5 if input.tenant_id != input.user_tenant_id

high_privilege_risk := 0
high_privilege_risk := 0.3 if input.action in ["write", "delete", "execute"]

#
# ============================================================
# 6. Approval Workflow
# ============================================================
#
requires_approval if {
    risk_score >= 0.7
}

requires_approval if {
    input.action == "delete"
}

requires_approval if {
    input.sensitivity == "confidential"
    input.action == "write"
}

requires_approval if {
    input.resource_type == "governance"
    input.action != "read"
}

#
# ============================================================
# 7. Final Allow Rules
# ============================================================
#

# --- READ ---
allow if {
    input.action == "read"
    tenant_check
    space_check
}

# --- WRITE (low risk) ---
allow if {
    input.action == "write"
    tenant_check
    space_check
    risk_score < 0.7
}

# --- WRITE (high risk, approved) ---
allow if {
    input.action == "write"
    tenant_check
    space_check
    risk_score >= 0.7
    input.approved == true
}

# --- DELETE (only with approval) ---
allow if {
    input.action == "delete"
    tenant_check
    space_check
    input.approved == true
}

# --- Ownership override ---
allow if ownership_allowed

# --- Role override ---
allow if role_allowed

#
# ============================================================
# 8. Reason Codes (Full)
# ============================================================
#
reason := "allowed" if allow

# Rego v1: rule body cannot be only a negated expression; use block with positive condition
reason := "tenant_mismatch" if {
    not tenant_check
    "tenant_mismatch"
}
reason := "space_access_denied" if {
    tenant_check
    not space_check
}
reason := "ownership_allowed" if ownership_allowed
reason := "role_allowed" if role_allowed

reason := "high_risk_requires_approval" if {
    tenant_check
    space_check
    risk_score >= 0.7
    not input.approved
}

reason := "approval_required" if requires_approval
# Rego v1: rule body cannot be only a negated expression
reason := "denied_by_policy" if {
    not allow
    "denied_by_policy"
}
