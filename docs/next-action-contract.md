# Next Action Contract

Scope: `app/(dashboard)/monitoring/page.tsx` only.  
Goal: remove ambiguity between click intent, mutation behavior, and visible outcome.

## Click Behavior by Kind

| kind | On click (exact) | Mutation | User-visible outcome |
|---|---|---|---|
| `failed` | Calls `tryCreateTaskFromNextAction` -> `createTaskV1`; if unavailable, opens run context panel (`beginRunContextForExecution(rid, null)`) | Real (task create) | `Creating task…` -> `Task created — now tracked` OR `Could not create — try again` OR `Action not available yet — opening flow` |
| `partial` | Same as `failed`, but unavailable fallback opens panel with `pending-steps` scroll intent | Real (task create) | Same message sequence as `failed` |
| `processing` | Opens run context panel only (`beginRunContextForExecution(rid, null)`) | View-only | Panel opens; run verification text updates |
| `completed` | Opens run context panel with `output` scroll intent | View-only | Panel opens at output area; verification text updates |
| `idle` | Placeholder/log path only (`start flow placeholder`) | None (guidance-only) | No server mutation; guidance copy only |

## Contract Rules

1. Only `failed` and `partial` are mutation paths in this flow.
2. `processing` and `completed` are strictly read/view actions.
3. `idle` never mutates state.
4. The card must always show action type explicitly:
   - `Real action (mutates state)`
   - `View-only (opens run context)`
   - `Guidance-only (no mutation)`

## Verification Path Contract

- After every non-idle click with `targetRunId`, `verifyRunAfterAction(runId)` is attempted.
- If visibility fetch does not return in the window, UI shows:
  - `Checking latest status…`
  - then `Update in progress`
- Verification never silently mutates user-visible headlines for `taskOutcome=created`; headline remains task-specific.
