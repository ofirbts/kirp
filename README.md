# KIRP Enterprise

Controlled Intelligence Layer · Event-Sourced · Multi-Tenant.

See [README_API.md](README_API.md) for Brand OS v3 API and full system documentation.

**Operators / audit:** [SYSTEM_STATUS.md](SYSTEM_STATUS.md) — Redis run keys, pipeline vs post-ingest, cross-store failures, idempotency, OPA semantics, metrics paths, regression test index. Architecture narrative: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md).

## Phase 1 & cloud deployment

- **What the system does and Phase 1 scope:** [docs/PHASE1_AND_DEPLOYMENT.md](docs/PHASE1_AND_DEPLOYMENT.md)
- **API on RunMyDocker:** [docs/RUNMYDOCKER.md](docs/RUNMYDOCKER.md). Env: copy `.env.example` to `.env` and set values.
- **UI on Vercel:** set `NEXT_PUBLIC_API_URL` (see `docs/env.local.example` or `.env.local`) and configure `CORS_ORIGINS` on the API.

## Quick Start (לראות משהו מהר)

**סכמה מלאה:** [docs/QUICKSTART.md](docs/QUICKSTART.md) — איך להריץ עם Docker, לפתוח דאשבורד (3100), M3 (רפלקציות), ופתרון בעיות נפוצות.

**בקצרה:** `docker compose up -d --build` → אחרי 1–2 דקות פתח http://localhost:3100 (דאשבורד) ו־http://localhost:3100/m3 (M3 Identity).

---

## Backend tests (pytest)

From the repo root (Python 3.10+):

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -q
```

Regression modules are indexed in [SYSTEM_STATUS.md](SYSTEM_STATUS.md) (**Regression test index**). CI: `.github/workflows/tests.yml` (branches **main**, **kirp2**).

---

## Building with Docker

If you see Docker buildx permission errors (e.g. `permission denied` under `~/.docker/buildx/`), run the reset script **before** building:

```bash
chmod +x scripts/reset_buildx.sh
./scripts/reset_buildx.sh
```

Then build and start all services:

```bash
docker compose down
docker compose up -d --build
```

The reset script fixes ownership and permissions for `~/.docker` and recreates the default buildx builder.

## Gemini CLI research agent (optional)

For ad-hoc research using Gemini + web tools, you can use the standalone CLI agent:

- Script: `agent.js`
- Env:
  - `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) – Gemini API key.
  - `GEMINI_MODEL` – model name, e.g. `gemini-1.5-flash` (see `node list_models.js`).

Usage:

```bash
# 1. Copy .env.example to .env and set GEMINI_API_KEY / GEMINI_MODEL

node list_models.js   # prints available models for your key
npm run agent         # runs agent.js with the default question
```

The agent will fetch web context (if `TAVILY_API_KEY` is set), call Gemini with tools,
and write a markdown summary to `research_results.md`.
