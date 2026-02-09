# KIRP Enterprise

Controlled Intelligence Layer · Event-Sourced · Multi-Tenant.

See [README_API.md](README_API.md) for Brand OS v3 API and full system documentation.

## Phase 1 & cloud deployment

- **What the system does and Phase 1 scope:** [docs/PHASE1_AND_DEPLOYMENT.md](docs/PHASE1_AND_DEPLOYMENT.md)
- **API on RunMyDocker:** [docs/RUNMYDOCKER.md](docs/RUNMYDOCKER.md). Env: copy `.env.example` to `.env` and set values.
- **UI on Vercel:** set `NEXT_PUBLIC_API_URL` (see `docs/env.local.example` or `.env.local`) and configure `CORS_ORIGINS` on the API.

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
