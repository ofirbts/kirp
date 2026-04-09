# OPA policies — source of truth

Policy files were consolidated. The single source of truth is:

**`deploy/opa/policies/kirp.rego`**

Docker Compose mounts `./deploy/opa/policies:/policies`. Use that folder for local OPA runs or copy from it here if needed.

**Runtime behavior:** when the API/worker is configured with a non-empty **`OPA_URL`**, OPA errors or non-200 responses **deny** writes before Mongo (fail-closed). Falsy URL disables HTTP checks. See **`SYSTEM_STATUS.md`** → **Governance / OPA**.
