# OPA policies — source of truth

Policy files were consolidated. The single source of truth is:

**`deploy/opa/policies/kirp.rego`**

Docker Compose mounts `./deploy/opa/policies:/policies`. Use that folder for local OPA runs or copy from it here if needed.
