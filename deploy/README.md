# Deploy — Docker WSL Setup + One-Command Launch

## Docker Desktop + WSL integration (Windows)

1. Open **Docker Desktop**.
2. Go to **Settings -> Resources -> WSL Integration**.
3. Enable integration for your WSL distro (the one where this repo runs).
4. Click **Apply & Restart**.
5. Restart your terminal/WSL session.

Validate:

```bash
docker --version
docker compose version
```

Both commands must work before launch.

## Launch command

From repo root:

```bash
./deploy/launch-prod.sh
```

This script will:
1. Copy `deploy/.env.prod.example` -> `.env.prod`
2. Start production stack from `deploy/docker-compose.prod.yml`
3. Run `deploy/smoke-test.sh` (health + onboarding + Stripe webhook signature flow)

## Quick health check

```bash
curl http://localhost:8080/health
```

Expected: JSON with `"status": "healthy"`.

## Notes

- Replace `.env.prod` placeholders with real production values before go-live.
- `src/main.py` has fail-fast validation in production for:
  - `STRIPE_SECRET_KEY`
  - `DATABASE_URL`
  - `REDIS_URL`
