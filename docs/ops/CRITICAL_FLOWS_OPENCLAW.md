# Critical Flows

## 1) Authentication and Authorization

Failure modes:
- invalid token path
- inconsistent permission checks
- silent auth failure

Verification:
- auth-protected endpoints reject invalid auth
- valid auth path remains stable

## 2) Data Flow and Business Logic Core

Failure modes:
- data corruption
- contract mismatch between layers
- side effects without expected trace

Verification:
- integration tests for core business path
- contract checks on changed boundaries

## 3) Error Handling and Logging

Failure modes:
- swallowed errors
- inconsistent error shape
- missing operational logs

Verification:
- expected error shape preserved
- key failure points produce logs

## 4) Deployment and Rollback

Failure modes:
- unknown runtime version
- no rollback trigger or command
- migration uncertainty

Verification:
- health check pass
- runtime version resolvable
- rollback plan executable

## 5) Testing Pipeline

Failure modes:
- tests skipped for critical paths
- false green due to missing integration coverage

Verification:
- required test suite runs for changed scope

Escalation:
- on critical flow failures, run `/debug` first
- route validation through Reviewer/Tester
- require Release Guard before production release
