PROJECT ?= kirp
COMPOSE ?= docker compose
COMPOSE_FILE ?= docker-compose.yml

E2E_SCRIPT ?= ./TEST_E2E.sh

.PHONY: help
help:
    @echo "KIRP Enterprise — Makefile"
    @echo ""
    @echo "Usage:"
    @echo "  make up           # start full stack"
    @echo "  make down         # stop stack"
    @echo "  make restart      # restart stack"
    @echo "  make reset        # down + remove volumes"
    @echo "  make ps           # list containers"
    @echo "  make logs         # tail all logs"
    @echo "  make logs-api     # tail API logs"
    @echo "  make logs-worker  # tail worker logs"
    @echo "  make logs-kafka   # tail kafka logs"
    @echo "  make status       # health summary"
    @echo "  make e2e          # run full E2E test suite"
    @echo "  make e2e-fast     # run E2E without reset"
    @echo "  make api-shell    # open shell in API container"
    @echo "  make worker-shell # open shell in worker container"

.PHONY: up
up:
    $(COMPOSE) -f $(COMPOSE_FILE) up -d

.PHONY: down
down:
    $(COMPOSE) -f $(COMPOSE_FILE) down

.PHONY: restart
restart: down up

.PHONY: reset
reset:
    $(COMPOSE) -f $(COMPOSE_FILE) down -v

.PHONY: ps
ps:
    $(COMPOSE) -f $(COMPOSE_FILE) ps

.PHONY: logs
logs:
    $(COMPOSE) -f $(COMPOSE_FILE) logs -f

.PHONY: logs-api
logs-api:
    $(COMPOSE) -f $(COMPOSE_FILE) logs -f kirp-api

.PHONY: logs-worker
logs-worker:
    $(COMPOSE) -f $(COMPOSE_FILE) logs -f kirp-worker

.PHONY: logs-kafka
logs-kafka:
    $(COMPOSE) -f $(COMPOSE_FILE) logs -f kirp-kafka

.PHONY: api-shell
api-shell:
    $(COMPOSE) -f $(COMPOSE_FILE) exec kirp-api /bin/bash

.PHONY: worker-shell
worker-shell:
    $(COMPOSE) -f $(COMPOSE_FILE) exec kirp-worker /bin/bash

.PHONY: status
status:
    @echo "🔍 Containers:"
    @$(COMPOSE) -f $(COMPOSE_FILE) ps
    @echo ""
    @echo "🔍 API health:"
    @curl -sf http://localhost:8000/health || echo "API not responding"
    @echo ""
    @echo "🔍 OPA health:"
    @curl -sf http://localhost:8181/health || echo "OPA not responding"
    @echo ""
    @echo "🔍 Qdrant health:"
    @curl -sf http://localhost:6333/healthz || echo "Qdrant not responding"
    @echo ""
    @echo "🔍 Elasticsearch health:"
    @curl -sf http://localhost:9200/_cluster/health || echo "ES not responding"

.PHONY: e2e
e2e: reset up
    @echo "⏳ Waiting for stack to stabilize..."
    @sleep 40
    $(E2E_SCRIPT)

.PHONY: e2e-fast
e2e-fast: up
    @echo "⏳ Waiting for stack to stabilize..."
    @sleep 20
    $(E2E_SCRIPT)
