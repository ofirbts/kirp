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
