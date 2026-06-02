# Incident Runbook (Launch)

## Redis down
- Switch to read-only mode where possible.
- Disable non-critical write paths.
- Restore Redis and run reconciliation.

## Stripe down
- Keep tenants in trial/grace mode temporarily.
- Queue billing retries.
- Replay webhooks after Stripe recovery.

## Pipeline failure > 20%
- Trigger forced reconciliation for partial runs.
- Monitor `kirp_pipeline_*` and run-controller states.
- Escalate if failure ratio stays above threshold.
