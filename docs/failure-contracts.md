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

### Verify State Contract (explicit, deterministic)

All post-action verification must resolve into exactly one of these states:

1. `processing`
2. `success`
3. `failure`
4. `network_issue`

No other user-visible state is allowed.

#### State: `processing`

- Trigger condition:
  - First visibility fetch does not return data within `8s` (timeout), and no transport error is raised.
  - Retry attempt also times out or returns non-terminal processing state (`accepted`/`processing`/`partial`).
- User-facing lines:
  - Headline: `Still processing — this can take a bit longer`
  - Proof line: `Run is still processing`
- Timeout rules:
  - Attempt #1 timeout: `8s`
  - Wait before retry: `1.5s`
  - Attempt #2 timeout: `8s`
- Fallback:
  - Keep current success context (if task created, keep "Task created — now tracked")
  - Show `Next:` continuation line
  - Never switch to generic error.

#### State: `success`

- Trigger condition:
  - Visibility fetch returns valid payload and run state indicates forward progress:
    - terminal success (`completed`) OR
    - non-terminal but positive progress (`processing`/`accepted`) after action.
- User-facing lines:
  - If completed: `Done — this is now resolved`
  - If progressed: `Progress resumed` (or task-created success headline if already shown)
  - Proof line:
    - completed: `"<last successful step>" finished · Flow completed successfully`
    - progressed: `Flow is continuing`
- Timeout rules:
  - Uses same two-attempt window; first valid success response ends verification immediately.
- Fallback:
  - If task was created, preserve `Task created — now tracked` as primary headline.

#### State: `failure`

- Trigger condition:
  - Visibility fetch returns valid payload with blocking state (`failed`) after action.
- User-facing lines:
  - Headline: `Still needs attention — details are in the panel`
  - Proof line: `Still blocked — needs attention`
- Timeout rules:
  - No extra retries beyond the two-attempt verify window.
- Fallback:
  - Keep panel-open path available for immediate context.
  - Do not claim completion or progress.

#### State: `network_issue`

- Trigger condition:
  - Visibility fetch throws transport/runtime error (DNS, connection reset, 5xx proxy error, offline) on any verify attempt.
- User-facing lines:
  - Headline: `Network issue while checking status`
  - Proof line: `Could not reach the server`
- Timeout rules:
  - Immediate classification on transport error (no additional blind retry loop).
- Fallback:
  - Action result remains visible (for example task-created outcome)
  - User can continue flow; page must not lock or spin indefinitely.

### Contract Rules

1. Exactly one verify state is shown at a time.
2. `network_issue` and `processing` must never share the same copy.
3. Verification never removes a stronger confirmed success headline (`Task created — now tracked`).
4. If verification cannot conclude, UI remains actionable and non-blocking.

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
