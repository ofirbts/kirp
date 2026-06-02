# Work Cadence

## Daily

1. pick one prioritized task
2. run `/plan-task`
3. for complex work, split to async subagents
4. for significant changes, use isolated worktree
5. for cross-module work, use multi-root workspace
6. implement in approved scope
7. run `/test`
8. update short change report

## Weekly

1. review top regressions and flaky areas
2. validate critical flow integration tests
3. review deploy and rollback readiness
4. clean unresolved technical risk list
5. convert recurring failures into rules or Bugbot learned rules

## Per Project Milestone

1. freeze scope for milestone
2. verify merge and deploy gates
3. run `/deploy-check`
4. record release evidence and rollback plan
