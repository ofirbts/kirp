# Runtime Versioning Contract

Goal: answer in under 10 seconds: "What exact version is this user running?"

## 1) Git SHA Injection Points

Canonical value: full git commit SHA (`40` chars).  
Short display value: first `7` chars.

### Build Step (CI or local release build)

1. Resolve SHA once at build start:
   - `GIT_SHA=$(git rev-parse HEAD)`
2. Pass SHA to image builds as build arg:
   - API image: `--build-arg APP_GIT_SHA=$GIT_SHA`
   - Dashboard image: `--build-arg NEXT_PUBLIC_APP_GIT_SHA=$GIT_SHA`
3. Persist SHA into image metadata:
   - OCI label: `org.opencontainers.image.revision=$GIT_SHA`

Contract: SHA is computed once and reused across all artifacts in a release.

## 2) Container Runtime Flow

### API container

- Dockerfile declares:
  - `ARG APP_GIT_SHA`
  - `ENV APP_GIT_SHA=$APP_GIT_SHA`
  - `LABEL org.opencontainers.image.revision=$APP_GIT_SHA`
- Runtime process reads `APP_GIT_SHA` from environment.

### Dashboard container

- Dockerfile declares:
  - `ARG NEXT_PUBLIC_APP_GIT_SHA`
  - `ENV NEXT_PUBLIC_APP_GIT_SHA=$NEXT_PUBLIC_APP_GIT_SHA`
  - `LABEL org.opencontainers.image.revision=$NEXT_PUBLIC_APP_GIT_SHA`
- Next.js exposes this via `process.env.NEXT_PUBLIC_APP_GIT_SHA`.

Contract: if env var missing, fallback must be literal `"unknown"` (never empty string).

## 3) API Exposure Contract

## Header

- Header name: `X-KIRP-Version`
- Value: full SHA or `"unknown"`
- Applied to: every API response (success and error)

## `/health` shape

`GET /health` response must include:

```json
{
  "status": "healthy",
  "event_store": "ok",
  "rag_engine": "ok",
  "version": {
    "sha": "40-char-sha-or-unknown",
    "short": "7-char-or-unknown",
    "source": "env:APP_GIT_SHA"
  }
}
```

Contract:
- `version.sha` is authoritative.
- `version.short` is presentation helper only.
- `source` explains where value was loaded from for debugging.

## 4) UI Read Contract

Primary source: `/health.version.sha` (runtime truth).  
Fallback source: `X-KIRP-Version` response header from any API call.  
Last fallback: `process.env.NEXT_PUBLIC_APP_GIT_SHA`.

Precedence:
1. `/health.version.sha` if non-empty and not `"unknown"`
2. `X-KIRP-Version` if non-empty and not `"unknown"`
3. `NEXT_PUBLIC_APP_GIT_SHA`
4. `"unknown"`

Contract: UI must store this as `runtimeVersion.sha` and never infer version from bundle timestamp.

## 5) Dashboard Rendering Contract

Render location: `app/(dashboard)/dashboard/page.tsx`, inside "System health" card.

Exact line:
- `Version: <short_sha> (<full_sha>)`
- If unknown: `Version: unknown`

Render rules:
- Show always in dev and staging.
- In production, show in debug mode only (e.g. query flag `?debug=1` or existing debug toggle).
- Value must be read-only text, no interaction.

## 6) Deterministic Acceptance Criteria

1. Same SHA appears in:
   - image label
   - `APP_GIT_SHA` env inside API container
   - `/health.version.sha`
   - `X-KIRP-Version`
   - dashboard debug display
2. Mismatch is a release blocker.
3. `"unknown"` in production is a release blocker.
