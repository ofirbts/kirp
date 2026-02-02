# KIRP Enterprise

Controlled Intelligence Layer · Event-Sourced · Multi-Tenant.

See [README_API.md](README_API.md) for Brand OS v3 API and full system documentation.

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
