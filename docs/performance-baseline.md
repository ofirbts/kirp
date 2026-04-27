# Performance Baseline

Environment: local docker runtime (`localhost`), measured from host against running stack.

Date: 2026-04-21  
Method: repeated HTTP calls with timed wall-clock, p50/p95 from sample distribution.

## Measurement Scope

1. **Dashboard load**: `GET /dashboard` (server response latency)
2. **Ask**: `POST /api/v1/ask`
3. **Next Action execution (proxy)**:
   - `POST /api/v1/tasks` (create task)
   - `GET /runs/{run_id}` (visibility check)

## Results

Samples:
- Dashboard: 40
- Ask: 25
- Next Action proxy: 25

Failures:
- Dashboard: 0
- Ask: 0
- Next Action proxy: 0

Latency (ms):

| Flow | p50 | p95 |
|---|---:|---:|
| Dashboard load | 6.6 | 35.0 |
| Ask | 900.1 | 2109.8 |
| Next Action execution (proxy) | 112.2 | 345.5 |

## Enforceable Gate (hard limits)

Baseline reference (`p95_ms`):

- dashboard_load: `35.0`
- ask: `2109.8`
- next_action_proxy: `345.5`

Hard thresholds (gate fails if any exceeded):

- dashboard_load_p95_ms <= `60`
- ask_p95_ms <= `2600`
- next_action_proxy_p95_ms <= `500`

Regression definition:

1. Absolute breach:
   - measured p95 > hard threshold -> **FAIL**
2. Relative regression:
   - measured p95 > baseline p95 * `1.20` (20% slower) -> **FAIL**
3. Combined strict rule:
   - check both absolute and relative; failing either is a failure.

## Measurement Script Contract

Script: `scripts/perf_check.py` (contracted behavior)

Inputs:

- `--baseline docs/perf-baseline.json`
- optional `--samples-dashboard` (default `40`)
- optional `--samples-ask` (default `25`)
- optional `--samples-next-action` (default `25`)

Execution behavior:

1. Run benchmark flows.
2. Compute p50/p95 per flow.
3. Compare measured p95 against:
   - baseline-relative threshold (20%)
   - absolute threshold table above
4. Print per-flow PASS/FAIL and reason.
5. Exit codes:
   - `0` all pass
   - `1` any regression/failure
   - `2` benchmark execution error (cannot measure)

Output artifacts:

- `artifacts/perf/latest-results.json`
- `artifacts/perf/latest-summary.md`

Required JSON shape:

```json
{
  "env": "local-docker",
  "timestamp": "ISO-8601",
  "flows": {
    "dashboard_load": { "p50_ms": 0, "p95_ms": 0, "status": "pass|fail", "reason": "" },
    "ask": { "p50_ms": 0, "p95_ms": 0, "status": "pass|fail", "reason": "" },
    "next_action_proxy": { "p50_ms": 0, "p95_ms": 0, "status": "pass|fail", "reason": "" }
  }
}
```

## CI Gate Contract

CI job name: `perf-regression-check`

Rules:

1. Must run on PRs touching:
   - `app/**`
   - `src/**`
   - `lib/apiClient.ts`
   - `docker-compose.yml`
2. Must fail pipeline on script exit code `1` or `2`.
3. Merge blocked unless job passes.

## Interpretation

- Dashboard server response is fast in current local baseline.
- Ask is the highest-latency path (RAG + LLM) and must remain inside declared threshold.
- Next Action proxy path is expected to stay materially below Ask latency.

## Limits

- Local docker performance is not production performance.
- Dashboard metric is server response latency, not full browser interaction timing.
- Next Action metric is backend proxy latency, not full click-to-render latency.
