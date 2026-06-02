# Onboarding Template

Use this template to onboard a new engineer to the OpenClaw workflow.

## 1) Mission

- Build safely and quickly without architecture drift.
- Follow the project operating system in `.cursor/` and `docs/ops/`.

## 2) Critical Flows

Read first:
- `docs/ops/CRITICAL_FLOWS_OPENCLAW.md`
- `docs/ops/DONE_CRITERIA_OPENCLAW.md`
- `docs/ops/RELEASE_RUNBOOK_OPENCLAW.md`

Never break:
- authentication and authorization
- data integrity and business flow
- API contracts
- error handling and logging
- deploy and rollback path

## 3) Daily Workflow

1. Run `/plan-task`
2. Implement approved scope only
3. Run `/test`
4. Report: what changed, why, risk, verify

For complex work:
- split into subagents
- use worktree for significant changes
- use multi-root when touching multiple modules

## 4) Subagent Roles

- Builder: implementation
- Reviewer/Tester: validation and regression checks
- Integrator: contract and boundary consistency
- Release Guard: merge and deploy readiness

## 5) Merge and Deploy Gates

Merge:
- lint, build, unit tests, critical integration tests, reviewer/tester signoff

Deploy:
- health check
- version check
- migration plan when needed
- rollback trigger and command

## 6) Escalation

If a critical failure happens:
1. run `/debug`
2. capture root cause evidence
3. apply minimal safe fix
4. rerun required validations
5. decide rollback or forward fix
