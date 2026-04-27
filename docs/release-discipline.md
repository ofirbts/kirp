# Release Discipline

Goal: deterministic path local -> PR -> deploy -> rollback, with no unknown runtime state.

## Non-negotiable Rules

1. No release from dirty tree.
2. No deploy without CI pass.
3. Every deployed artifact must be traceable to a git commit SHA.
4. Rollback must be executable in one command/runbook step.

## Commit Rules

- Keep commits atomic by behavior contract.
- Include tests for behavior changes.
- Never leave generated or local-only files unreviewed in release commits.
- Before commit:
  - `git status` clean except intended files
  - lint/test commands pass for touched scope

## PR Rules (minimum gate)

PR must include:
1. Behavior delta (before/after)
2. Risk assessment
3. Test evidence (commands + outputs)
4. Rollback note
5. Linked contract docs when behavior semantics changed

Required checks:
- unit/integration suite
- lint
- build (for dashboard changes)

## Automatable PR Template (exact text)

This exact template is required in `.github/pull_request_template.md`:

```md
## Behavior change
- What changed in user-visible behavior?
- Why is this change needed now?

## Contract impact
- Which contract docs changed? (list paths)
- If none, explain why behavior contract is unchanged.

## Test proof
- [ ] Unit/integration tests run
- [ ] Lint run
- [ ] Build run (if frontend touched)
- Commands executed:
  - `...`
- Key output:
  - `...`

## Performance impact
- [ ] No expected impact
- [ ] Measured with perf script
- Perf result link/artifact:
  - `...`

## Rollback plan
- Previous known-good SHA:
  - `...`
- Rollback command/runbook step:
  - `...`
- Rollback trigger:
  - `...`

## Release checklist
- [ ] No uncommitted local changes before final test
- [ ] PR includes behavior/test/rollback sections
- [ ] Required CI checks passed
- [ ] Version traceability confirmed (SHA in runtime contract)
```

## Required Fields (blocking if missing)

A PR is invalid unless all fields are present:

1. `Behavior change`
2. `Contract impact`
3. `Test proof` with commands
4. `Rollback plan` with previous SHA
5. `Release checklist` fully checked

## Automation Contract

Enforce with CI checks:

1. **Dirty tree guard (pre-push/local CI)**
   - fail if `git status --porcelain` is non-empty before release step
2. **PR template validator**
   - fail if required headings/checklist are missing
3. **Required status checks**
   - `lint`
   - `tests`
   - `build` (when frontend files touched)
   - `perf-regression-check` (when critical paths touched)

Merge policy:

- Direct pushes to protected release branch are blocked.
- Only PR merge with all required checks passing is allowed.

## Deploy Steps (minimum safe flow)

1. Merge PR to release branch.
2. Build immutable artifact with commit label.
3. Deploy to staging and run smoke checks:
   - `/health`
   - core user flow (login, ingest, ask, task create)
4. Promote same artifact to production.
5. Post-deploy verification with timestamped evidence.

## Rollback Rule

- Trigger rollback immediately if any of these fail post-deploy:
  - `/health` degraded for > N minutes
  - Ask hard-fail rate above SLO
  - Task creation path regresses
- Roll back to previous known-good artifact SHA (no hot edits on live container).

## Explainability Contract

Every production deploy must be answerable with:

1. PR link
2. merged commit SHA
3. runtime SHA (`/health.version.sha`)
4. test evidence used for approval
5. explicit rollback command

If any item is missing, deploy is non-compliant.

## Current Deploy State Snapshot (documentation requirement)

Captured locally at contract-write time:

- `kirp-api`: Up, healthy, port `8000`
- `kirp-dashboard`: Up, port `3100`
- `kirp-postgres`: Up, healthy, port `5432`
- `kirp-qdrant`: Up, healthy, port `6333/6334`

Note: this is a runtime snapshot only, not a guarantee of production commit traceability.
Production traceability still requires artifact -> commit SHA mapping in CI/CD.
