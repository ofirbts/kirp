# Implementation Plan: UI/UX Modernization & Backend Hardening

This plan outlines the steps and task breakdown to modernize the visual interface of the KIRP dashboard (making it match the premium references) and harden the backend services (resolving structural, consistency, and idempotency gaps).

---

## User Review Required

> [!IMPORTANT]
> **Subagents Defined:** We have defined three specialized subagents (`ui_ux_designer`, `e2e_verifier`, and `architect_hardening`) to execute specific tasks concurrently and cost-effectively.
> **Breaking Change Warning:** Moving from inline engine initialization to a central dependency injection registry could cause temporary import failures if not merged carefully.
> **Security Isolation:** Transitioning Qdrant from logical filtering to separate collections is out of scope for the initial hardening phase but is recommended for the production launch.

---

## Open Questions

> [!WARNING]
> Do you have local font files for `Gilroy`, or should we use the open-source Google Font `Outfit` as a baseline?
> Do you want the M3 reflection stages (`run_m3_stages`) to be asynchronous by default via Celery, or should we keep a synchronous override flag for debugging?

---

## Proposed Changes

### Component 1: UI/UX Modernization

#### [MODIFY] [tailwind.config.cjs](file:///wsl.localhost/Ubuntu-22.04/home/ofir/projects/kirp/tailwind.config.cjs)
* Add custom typography configuration for `Outfit` / `Plus Jakarta Sans`.
* Define pastel palettes: peach, teal (mint), purple (lilac), and warm coral HSL codes.

#### [MODIFY] [app/globals.css](file:///wsl.localhost/Ubuntu-22.04/home/ofir/projects/kirp/app/globals.css)
* Add Google Fonts `@import` rule for the chosen typography.
* Define global glassmorphism utility classes and soft shadow variants.

#### [MODIFY] [app/(dashboard)/m3/page.tsx](file:///wsl.localhost/Ubuntu-22.04/home/ofir/projects/kirp/app/(dashboard)/m3/page.tsx)
* Refactor reflection inputs, cards, and micro-actions lists to use glassmorphism and HSL gradients.
* Add Framer Motion animations to components for fade-in entry and bouncy click interactions.

---

### Component 2: Backend Hardening

#### [NEW] [registry.py](file:///wsl.localhost/Ubuntu-22.04/home/ofir/projects/kirp/src/core/registry.py)
* Create a central `ServiceRegistry` singleton managing connections to MongoDB, PostgreSQL, Qdrant, Redis, and OPA.
* Implement lazy initialization and proper connection health check hooks.

#### [NEW] [idempotency.py](file:///wsl.localhost/Ubuntu-22.04/home/ofir/projects/kirp/src/core/idempotency.py)
* Create a unified `IdempotencyProvider` that handles both Kafka ingest checks and HTTP `Idempotency-Key` headers.

#### [MODIFY] [pipeline.py](file:///wsl.localhost/Ubuntu-22.04/home/ofir/projects/kirp/src/core/pipeline.py)
* Integrate `ServiceRegistry` singletons to replace inline instantiation of `EventStore`, `RAGEngine`, `SchemaEngine`, and `GovernanceEngine`.
* Refactor projections (Qdrant & Postgres) to write to an outbox table in MongoDB upon failure, making projection reconciliation fully deterministic.

---

## Verification Plan

### Automated Tests
* Run the existing regression test suites to ensure zero breakage:
  ```bash
  pytest tests/
  ```
* Run the End-to-End test suite to verify full-stack message processing:
  ```bash
  ./TEST_E2E.sh
  ```

### Manual Verification
* Run Next.js locally and review the updated visual styles:
  ```bash
  npm run dev
  ```
* Inspect components using the browser development tools to ensure correct font rendering (`Outfit` / `Plus Jakarta Sans`), glassmorphism styles, and Framer Motion spring physics.
