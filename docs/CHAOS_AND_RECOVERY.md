# Chaos and recovery

For each chaos dimension: **current behavior** (from code paths), **expected behavior** for a mature platform, **missing safeguards**, **danger level** (Low / Medium / High).

## Broker restart (Kafka)

| Aspect | Current | Expected | Missing | Danger |
| ------ | ------- | -------- | ------- | ------ |
| Consumer offset | Uncommitted offsets replay | Controlled replay | DLQ for poison | **Medium** |
| Producer during API call | `flush(5s)` then fail | Backpressure / queue | Client retry storm | **Medium** |
| Topic create | AdminClient on processor startup | Infra-as-code | **Low** |

## Redis restart

| Aspect | Current | Expected | Missing | Danger |
| ------ | ------- | -------- | ------- | ------ |
| Run state | Loss of visibility; in-memory fallback may mask outage | HA Redis / persistence | Alerting on `redis_health` false | **High** for ops |
| Idempotency keys | Lost → duplicate processing window | Longer TTL + tenant-prefixed keys + txn outbox | **High** for correctness |

## DB reconnect (Mongo / Postgres)

| Aspect | Current | Expected | Missing | Danger |
| ------ | ------- | -------- | ------- | ------ |
| Motor / SQLAlchemy | Motor connects lazily; pool_pre_ping on sync Postgres engine | Auto-heal | **UNVERIFIED** async SQLAlchemy paths | **Medium** |

## Partial deploy (API up, worker down)

| Aspect | Current | Missing | Danger |
| ------ | ------- | ------- | ------ |
| Ingest | Kafka buffer fills / producer error | Lag alert | **Medium** |

## Stale workers

| Aspect | Current | Missing | Danger |
| ------ | ------- | ------- | ------ |
| Old code version | `X-KIRP-Version` header on responses | Deploy coordination | **Low** visibility, **Medium** risk during rollout |

## Stuck retries / poison messages

| Aspect | Current | Missing | Danger |
| ------ | ------- | ------- | ------ |
| Repeated failure | Offset not committed; blocks partition progress for that message in single-threaded loop | DLQ + skip policy | **High** |
| `move_to_dlq` | Exists in EventStore | **Not wired** in `kafka_processor` failure exit path (audited) | **High** |

## Backpressure

| Aspect | Current | Missing | Danger |
| ------ | ------- | ------- | ------ |
| Consumer | Serial `await process_event` | Parallelism / partition scaling ops | **Medium** |
| API | No ingest rate limit per tenant | Quota middleware partial elsewhere | **UNVERIFIED** |

## Queue buildup

| Detection | Current |
| --------- | ------- |
| Lag | External Kafka metrics—**not** first-class in `/health` |

## Cold start

| Aspect | Current |
| ------ | ------- |
| API | Lazy singletons; first request may spike latency |
| Worker | `wait_for_topic` infinite loop until topic exists |

## Orphaned state

| Scenario | Current |
| -------- | ------- |
| `run_id` without pipeline | `PIPELINE_RUN_POLICY` strict vs warn; orphan metrics `orphan_run_id_total` |
| Redis run without Mongo event | **UNVERIFIED** reconciliation job |

---

## Recovery playbooks (code-aligned)

1. **Kafka lag growing:** check `kirp-agent-processor` logs for `kafka_processor_failed`; fix dependency; consumer resumes from last commit.
2. **Redis empty:** expect duplicate processing and run steps missing—**treat Redis as critical** for production multi-instance.
3. **Poison message:** today likely requires manual skip or topic surgery—**missing productized DLQ** from processor to `move_to_dlq`.
