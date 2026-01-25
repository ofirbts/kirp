package kirp.governance

import rego.v1

default allow := false

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
    requires_approval
}

tenant_check if {
    input.tenant_id == input.user_tenant_id
}

tenant_check if {
    input.tenant_id != input.user_tenant_id
    input.cross_tenant_grant == true
}

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

risk_score := score if {
    score := sum([
        confidential_risk,
        delete_risk,
        governance_risk,
        autonomy_risk,
    ])
}

confidential_risk := 0
confidential_risk := 0.3 if {
    input.sensitivity == "confidential"
}

delete_risk := 0
delete_risk := 0.4 if {
    input.action == "delete"
}

governance_risk := 0
governance_risk := 0.2 if {
    input.resource_type == "governance"
}

autonomy_risk := 0
autonomy_risk := 0.1 if {
    input.agent_autonomy == "full"
}

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

reason := "policy_check" if allow
reason := "tenant_mismatch" if not tenant_check
reason := "space_access_denied" if tenant_check and not space_check
reason := "high_risk_requires_approval" if {
    tenant_check
    space_check
    risk_score >= 0.7
    not input.approved
}
reason := "denied_by_policy" if not allow
