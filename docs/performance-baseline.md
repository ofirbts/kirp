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

## Interpretation

- Dashboard server response is fast in current local baseline.
- Ask is the highest-latency path (RAG + LLM); this is expected and should be tracked as a dedicated SLO.
- Next Action backend mutation+verification path is materially faster than Ask.

## Limits of This Baseline

- Local docker performance is not production performance.
- Dashboard metric is HTTP response latency, not full browser paint/interactive timing.
- Next Action metric is backend proxy (task + visibility), not full click-to-UI-render.

## Next Baseline Upgrade (required)

To make this production-grade:
1. Add browser-level click-to-visible timers (RUM/synthetic).
2. Track p95 continuously (not one-off) in observability.
3. Store metrics with commit SHA and environment labels.
