# KIRP User Guide

## Purpose

This guide defines the standard way to run KIRP as a managed engineering system using Cursor.

## What Changed

KIRP now runs with an explicit operating layer:

- Rules for scope, safety, critical flows, tests, and release gates
- Commands for repeatable execution (`/plan-task`, `/implement-safe`, `/test`, `/refactor-safe`, `/deploy-check`)
- Hooks for pre-task reflection, shell safety, pre-commit caution, and post-failure debug prompts
- Subagent role model: Builder, Reviewer/Tester, Integrator, Release Guard
- Ops docs for flows, done criteria, rollback, cadence, and incident handling
- Ops dashboard canvas for at-a-glance operational control

## Cursor 3.2+ Features In Workflow

- Async subagent split for complex tasks
- Isolated worktree recommendation for significant changes
- Multi-root recommendation for cross-module changes
- Canvas as live operational dashboard and planning artifact
- `/debug` as first response to critical failures
- `/config` recommendation when model/tool behavior must change
- Rule-driven improvement path for recurring issues (Bugbot learned-rules style)

## Daily Workflow

1. Start with `/plan-task`
2. Confirm scope boundaries and risks
3. Split to subagents when complexity requires parallel execution
4. Implement via `/implement-safe`
5. Validate via `/test`
6. Report each change in format: what / why / risk / verify

## Weekly Workflow

1. Review repeated failures and flaky checks
2. Review critical flow reliability
3. Run release readiness checks (`/deploy-check`)
4. Update rules and playbooks from repeated incidents

## Release Workflow

1. Confirm merge gates pass
2. Confirm health and runtime version checks
3. Confirm migration and rollback readiness
4. Release only after Release Guard validation

## Subagent Usage

- Builder: scoped implementation
- Reviewer/Tester: quality and regression checks
- Integrator: boundary and contract consistency
- Release Guard: release safety and evidence gate

## Ops Dashboard Usage

Use the canvas dashboard to track:

- critical flows and guardrails
- daily and weekly cadence
- active baseline of rules, commands, and hooks
- before vs after efficiency profile

Recommended routine:

- Check once at task start (daily)
- Check once before merge or deploy
- Check during weekly risk review
