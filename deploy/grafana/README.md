# Grafana — KIRP pipeline dashboard

## Import

1. Grafana → **Dashboards** → **Import** → upload `kirp_pipeline_dashboard.json`.
2. Select your **Prometheus** datasource when prompted (template variable `datasource`).

## Prometheus scrape

Counters (`kirp_pipeline_no_run_id_total`, `kirp_pipeline_orphan_run_id_total`) are exposed on the API at:

`GET /observability/metrics/prometheus`

Ensure `deploy/prometheus.yml` (or your Helm values) uses that **metrics_path** for the `kirp-api` job. Metrics are no-ops when `DISABLE_PROMETHEUS=1` or `prometheus_client` is missing.

## Panels

- **Rate (5m)** of no-run-id and orphan-run-id events, by `event_type` and `source`.
- **Stat:** 1h increases for quick SLO-style checks.

## Related

- **`SYSTEM_STATUS.md`** — **Metrics exposure** (scrape path, `DISABLE_PROMETHEUS`) and **Regression test index** (includes **`tests/test_observability_metrics.py`** for route smoke).
- **`deploy/KIRP_PRODUCTION_ONEPAGER.md`** — customer-facing capability map + pointers to dashboards and scrape config.
