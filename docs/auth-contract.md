# Auth Contract

Scope: frontend API client + backend JWT-protected endpoints.

## Single Source Auth Client

Source of truth: `lib/apiClient.ts`.

- Token lookup order:
  1. `localStorage.access_token` / `kirp_auth_token` / `kirp_token`
  2. `sessionStorage.access_token` / `kirp_auth_token` / `kirp_token`
  3. `NEXT_PUBLIC_DEV_TOKEN` fallback
- `authHeaders()` injects `Authorization: Bearer <token>` when token exists.
- All client wrappers (`get`, `post`, `patch`, `getJson`) include:
  - `credentials: "include"`
  - `...authHeaders()`

Contract: UI code should not bypass this client for protected endpoints.

## Injection Rules

1. Protected endpoints must be called via `apiClient` wrappers.
2. Token must be present in runtime storage for authenticated sessions.
3. Tenant/user context must come from JWT on backend (`/api/v1/*`).

## Retry Policy

Current policy:
- No global auth refresh pipeline in `apiClient` wrappers.
- Request fails fast on non-2xx and throws explicit error.

Required deterministic policy (hardening target):
1. On first `401`, attempt one token-refresh/reauth path (if available).
2. Retry exactly once.
3. If still unauthorized, force logged-out UX state and route to login.

## User-visible Auth Failure Contract

- Any `401` / `403` must surface explicit state (not silent):
  - banner/toast/inline error with endpoint-level message
  - deterministic CTA (`Re-login`)
- Mid-session auth failures must not leave partial “loading forever” states.

## Known Break Points (today)

Observed in runtime logs:
- `/api/v1/llm/usage` can return `401` mid-session.
- `/api/v1/tenant/{tenant_id}/alerts` can return `403` mid-session.

Hardening requirement:
- Instrument and alert on unexpected auth failures by endpoint + tenant + user/session.
