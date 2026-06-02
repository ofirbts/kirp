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

Contract: UI code must not bypass this client for protected endpoints.

## Injection Rules

1. Protected endpoints must be called via `apiClient` wrappers.
2. Token must be present in runtime storage for authenticated sessions.
3. Tenant/user context must come from JWT on backend (`/api/v1/*`).

## Token Lifecycle (deterministic)

1. Access token is attached on every request via `Authorization: Bearer <token>`.
2. Access token is short-lived (contract target: 15 minutes).
3. Refresh token is HTTP-only cookie (contract target: 7 days), never stored in JS-readable storage.
4. Client keeps only access token in memory/storage; refresh token is server-managed.
5. On app bootstrap:
   - If access token exists, use it immediately.
   - If missing/expired, attempt refresh once before declaring session invalid.

## Refresh Timing

Two allowed refresh paths only:

1. **Reactive refresh (required)**  
   Trigger: request returns `401`.
2. **Bootstrap refresh (required)**  
   Trigger: app load with no valid access token but refresh cookie may exist.

No background refresh loop, no polling refresh, no multi-refresh race.

## Retry Rules (exact numbers)

1. On `401`:
   - attempt refresh exactly `1` time
   - retry original request exactly `1` time
2. On `403`:
   - do not refresh
   - do not retry automatically
3. Maximum total attempts per request:
   - `2` attempts for `401` path (original + one retried call)
   - `1` attempt for `403` path
4. If refresh endpoint fails (`401/403/5xx/network`):
   - mark auth state as invalid immediately
   - do not repeat refresh for the same request chain

## Request Interceptor Contract

All wrappers (`get`, `post`, `patch`, `getJson`) must pass through one shared request path that:

1. injects auth headers
2. handles `credentials: "include"`
3. applies the single retry policy above
4. logs every `401`/`403` with context:
   - method
   - endpoint path
   - status code
   - retry attempt index
   - `hasToken` boolean

No endpoint-specific auth logic is allowed in feature components.

## User-visible Auth Failure Contract

### Mid-session `401` recovered by refresh

- User sees nothing disruptive.
- Original action completes normally after one internal retry.

### Mid-session `401` not recoverable

- User-visible line: `Your session expired. Please sign in again.`
- Deterministic CTA: `Go to login`
- App behavior:
  - clear local access token
  - transition to logged-out state
  - redirect to login route

### `403` authorization failure

- User-visible line: `You do not have permission for this action.`
- Deterministic CTA: `Back to dashboard`
- App behavior:
  - keep session (no forced logout)
  - stop retry attempts

### UX invariants

1. No silent auth failures.
2. No infinite spinners on auth errors.
3. One visible state per failed request (no overlapping toasts with conflicting actions).

## Known Break Points (today)

Observed in runtime logs:
- `/api/v1/llm/usage` can return `401` mid-session.
- `/api/v1/tenant/{tenant_id}/alerts` can return `403` mid-session.

Hardening requirement:
- Instrument and alert on unexpected auth failures by endpoint + tenant + user/session.
