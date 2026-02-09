#
# KIRP Governance Policy — Tenant, Space, Role, Risk, Approval, Reason
#
# Single package; complete and deterministic. Safe for missing/undefined input.
# Input (all optional): tenant_id, user_tenant_id, user_id, space_id, space_owner_id,
#   space_members (array), user_role, roles (array), resource_owner_id, action,
#   approved (bool), sensitivity, resource_type, agent_autonomy, cross_tenant_grant (bool).
#
package kirp.governance

import rego.v1

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
default allow := false
default requires_approval := false
default risk_score := 0
default role_allowed := false
default ownership_allowed := false

# ---------------------------------------------------------------------------
# 1. Tenant isolation
# ---------------------------------------------------------------------------
tenant_check if {
	input.tenant_id == input.user_tenant_id
}
tenant_check if {
	input.tenant_id != input.user_tenant_id
	input.cross_tenant_grant == true
}

# ---------------------------------------------------------------------------
# 2. Space access — safe: use iteration so wrong type (e.g. string) doesn't match
# ---------------------------------------------------------------------------
space_check if {
	input.space_id == "private"
	input.user_id == input.space_owner_id
}
space_check if {
	input.space_id == "shared"
	some m in input.space_members
	m == input.user_id
}
space_check if {
	input.space_id == "org"
	input.user_role in ["admin", "member"]
}
# Tenant-wide space (UI/API use "all" or "default")
space_check if {
	input.space_id in ["all", "default"]
}

# ---------------------------------------------------------------------------
# 3. Ownership override — only when resource_owner_id set and matches
# ---------------------------------------------------------------------------
ownership_allowed if {
	input.resource_owner_id != ""
	input.user_id == input.resource_owner_id
}

# ---------------------------------------------------------------------------
# 4. Role override — safe: iterate roles so string input doesn't match
# ---------------------------------------------------------------------------
role_allowed if {
	some r in input.roles
	r == "tenant-admin"
}
role_allowed if {
	some r in input.roles
	r == "space-admin"
	input.space_id != ""
}
role_allowed if {
	some r in input.roles
	r == "governance-admin"
}

# ---------------------------------------------------------------------------
# 5. Risk — single-valued; missing input => 0
# ---------------------------------------------------------------------------
confidential_risk := 0.3 if { input.sensitivity == "confidential" }
confidential_risk := 0 if { not input.sensitivity == "confidential" }

delete_risk := 0.4 if { input.action == "delete" }
delete_risk := 0 if { input.action != "delete" }

governance_risk := 0.2 if { input.resource_type == "governance" }
governance_risk := 0 if { input.resource_type != "governance" }

autonomy_risk := 0.1 if { input.agent_autonomy == "full" }
autonomy_risk := 0 if { input.agent_autonomy != "full" }

cross_tenant_risk := 0.5 if { input.tenant_id != input.user_tenant_id }
cross_tenant_risk := 0 if { input.tenant_id == input.user_tenant_id }

high_privilege_risk := 0.3 if { input.action in ["write", "delete", "execute"] }
high_privilege_risk := 0 if { not input.action in ["write", "delete", "execute"] }

risk_score := s if {
	s := confidential_risk + delete_risk + governance_risk + autonomy_risk + cross_tenant_risk + high_privilege_risk
}

# ---------------------------------------------------------------------------
# 6. Approval
# ---------------------------------------------------------------------------
requires_approval if { risk_score >= 0.7 }
requires_approval if { input.action == "delete" }
requires_approval if {
	input.sensitivity == "confidential"
	input.action == "write"
}
requires_approval if {
	input.resource_type == "governance"
	input.action != "read"
}

# ---------------------------------------------------------------------------
# 7. Allow — overrides first, then read, then one write rule, then delete
# ---------------------------------------------------------------------------
allow if { ownership_allowed }
allow if { role_allowed }
allow if {
	input.action == "read"
	tenant_check
	space_check
}
allow if {
	input.action == "write"
	tenant_check
	space_check
	risk_score < 0.7
}
allow if {
	input.action == "write"
	tenant_check
	space_check
	risk_score >= 0.7
	input.approved == true
}
allow if {
	input.action == "delete"
	tenant_check
	space_check
	input.approved == true
}

# ---------------------------------------------------------------------------
# 8. Reason — single complete rule, one output (rego.v1: each branch needs "if")
# ---------------------------------------------------------------------------
reason = r if {
	allow
	r := "allowed"
} else if {
	not tenant_check
	r := "tenant_mismatch"
} else if {
	tenant_check
	not space_check
	r := "space_access_denied"
} else if {
	tenant_check
	space_check
	input.action == "write"
	risk_score >= 0.7
	not input.approved
	r := "high_risk_requires_approval"
} else if {
	tenant_check
	space_check
	input.action == "delete"
	not input.approved
	r := "delete_requires_approval"
} else if {
	requires_approval
	r := "approval_required"
} else if {
	r := "denied_by_policy"
}
