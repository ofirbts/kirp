# Rollback and Deploy Checks

## Pre-Deploy

1. lint, build, tests pass
2. health check target ready
3. version check target resolvable
4. migration plan present when relevant
5. rollback command prepared
6. rollback trigger defined

## Rollback Trigger Examples

- health degraded for sustained window
- contract-breaking runtime errors
- critical flow regression

## Rollback Record

- release id or commit
- reason
- trigger evidence
- execution time
- post-rollback health status
