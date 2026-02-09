# KIRP Architecture (High-Level)

## Core Pipeline
ingest → event → governance → store → embed → schema → history/tasks/graph/insights

## Multi-tenancy
Every flow carries: tenant_id, space_id, user_id.

## Agents
Agents live in src/agents and are invoked via events or /api/v1/agents/*.

## Governance
OPA + internal governance layer. All external actions go through governance.

