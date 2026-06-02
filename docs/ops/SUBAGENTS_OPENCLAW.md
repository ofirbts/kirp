# OpenClaw Subagents

## Roles

### Builder
- Implements approved changes
- Keeps scope tight
- Produces minimal diffs

### Reviewer/Tester
- Reviews risk and regressions
- Runs lint, build, unit, and relevant integration tests
- Verifies Definition of Done

### Integrator
- Owns integration boundaries and contract fit
- Verifies compatibility across touched modules
- Confirms no contract break

### Release Guard
- Verifies merge gates and deploy gates
- Confirms health, version, migration, rollback readiness
- Blocks release on missing evidence

## Default Hand-off

1. Builder
2. Reviewer/Tester
3. Integrator when cross-boundary impact exists
4. Release Guard for merge/deploy readiness

## Suggested Model Weight

- Builder: medium
- Reviewer/Tester: medium-high on risky changes
- Integrator: high for multi-module changes
- Release Guard: medium
