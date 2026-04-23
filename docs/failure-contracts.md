# Failure Contracts

This file defines user-visible and system fallback behavior for critical paths.

## 1) `createTaskV1` (Next Action mutation path)

Code path: `tryCreateTaskFromNextAction` in `app/(dashboard)/monitoring/page.tsx`.

### Failure modes

1. **Transport/runtime exception** (network failure, backend unavailable, timeout)
2. **Non-success response shape** (`ok` false or no `data.id`)
3. **Missing `targetRunId`**

### User sees

- Always immediate: `Creating task…`
- Then:
  - transport exception -> `Action not available yet — opening flow` (fallback path)
  - non-success response -> `Could not create — try again`
  - missing run id -> no mutation, no create confirmation

### System behavior

- Transport exception -> return `taskOutcome="unavailable"` and open existing run-context fallback panel.
- Non-success response -> return `taskOutcome="failed"` (no task created).
- Success -> return `taskOutcome="created"` and continue verification loop.

No silent failure is allowed.

---

## 2) `getRunVisibilityV1` (verification after action)

Code path: `verifyRunAfterAction` / `fetchRunVisibilityOnce`.

### Failure modes

1. First fetch timeout/exception
2. Retry fetch timeout/exception
3. Returns malformed/unexpected state

### User sees

- If first fetch fails: `Checking latest status…`
- If retry also fails: `Update in progress` + proof line `Update in progress`

### System behavior

- Performs one retry after a short delay.
- Returns `null` if verification still unavailable.
- Keeps action feedback and loop state; does not crash the page.

No silent failure is allowed.

---

## 3) `/api/v1/ask` endpoint

Code path: `src/main.py` + `src/agents/insight.py`.

### Failure modes

1. Auth invalid/expired -> `401`
2. RAG backend unavailable at initialization
3. RAG search failure/timeout during ask
4. Unexpected internal exception

### User sees

- `401` -> auth error message from client path (`401: ...`)
- RAG unavailable -> fallback answer body (no hard crash)
- RAG search timeout -> fallback answer body (no hard crash)
- Unexpected internal exception -> `500: ...` (explicit error text)

### System behavior

- RAG init failure in `main.py` ask route returns a graceful response:
  - `answer` explains vector store unavailable
  - `sources=[]`, `needs_external_info=true`
- RAG search failure in `InsightAgent.ask` returns graceful fallback answer.
- Logs errors/warnings with context; endpoint should avoid silent nulls.

No silent failure is allowed.
