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

## Current Deploy State Snapshot (documentation requirement)

Captured locally at contract-write time:

- `kirp-api`: Up, healthy, port `8000`
- `kirp-dashboard`: Up, port `3100`
- `kirp-postgres`: Up, healthy, port `5432`
- `kirp-qdrant`: Up, healthy, port `6333/6334`

Note: this is a runtime snapshot only, not a guarantee of production commit traceability.
Production traceability still requires artifact -> commit SHA mapping in CI/CD.
