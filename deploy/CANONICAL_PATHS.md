# נתיבים קנוניים — Docker ו־Runtime

כשמריצים Docker או סקריפטים, יש להשתמש **רק** בנתיבים האלה. לא לגבות, לא ל־opa_policies_live, לא ל־KIRP_old.

## Docker Compose (docker-compose.yml)

| שירות | Dockerfile | Entrypoint / מה רץ |
|--------|------------|---------------------|
| **kirp-api** | `Dockerfile.api` (שורש) | **רק** `uvicorn src.main:app` — **src/main.py** (לא api.main = Brand OS) |
| **kirp-worker** | `Dockerfile.worker` | `celery -A src.workers.celery_app` |
| **kirp-agent-processor** | `Dockerfile.agent` | `python -m src.workers.kafka_processor` |
| **kirp-dashboard** | `Dockerfile.dashboard` | `streamlit run src/ui/master_dashboard.py` |
| **brand-os-api** | `Dockerfile.brand_os_api` | `uvicorn api.main:app` — **api/main.py** (Brand OS נפרד) |
| **opa** | — | image: openpolicyagent/opa, טוען **./deploy/opa/policies** → `/policies` |
| **qdrant** | `deploy/Dockerfile.qdrant` | image רשמי + curl |

## מדיניות OPA (Rego)

- **מקור אמת יחיד:** `deploy/opa/policies/kirp.rego`
- ה־volume ב־docker-compose: `./deploy/opa/policies:/policies`
- **לא** להשתמש ב־opa_policies_live (ריק/README בלבד)

## Postgres / Prometheus

- Init: `./deploy/postgres-init` → `/docker-entrypoint-initdb.d`
- Prometheus config: `./deploy/prometheus.yml`

## .dockerignore

ב־.dockerignore מוחרגים: `backup_pre_runmydocker/`, `opa_policies_live/`, `KIRP_old/`, `final.yml`, `n8n_data/` — כדי שהבילד יעתיק רק את הקבצים הנכונים.
