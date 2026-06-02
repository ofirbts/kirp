# OpenClaw Working Model

## Goal

Stable and fast delivery without architecture drift.

## Constraints

- No scope expansion without explicit approval
- No breaking critical flows
- No API/DB/infra/auth changes without approval

## Critical Flows

1. Authentication and authorization
2. Core data flow and business logic
3. Error handling and logging
4. Deployment and rollback
5. Testing pipeline

## Required Change Report

For each substantive change:
- what changed
- why
- risk
- what to verify
