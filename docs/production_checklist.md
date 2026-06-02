### KIRP Enterprise — Production Readiness Checklist

#### 1. Required environment variables

- **Core**
  - `MONGO_URI` — MongoDB connection (including authSource).
  - `POSTGRES_URI` — Postgres connection for SchemaEngine.
  - `QDRANT_URL`, `QDRANT_COLLECTION`, `QDRANT_API_KEY` (optional).
- **Security**
  - `JWT_SECRET` — strong, random secret (min 32 bytes).
  - `JWT_SECRET_PREVIOUS` — previous secret for rotation (optional).
  - `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` or `JWT_EXPIRES_IN`.
  - `CORS_ORIGINS` — comma-separated list of allowed UI origins (e.g. `https://app.kirp.com`).
- **UI**
  - `NEXT_PUBLIC_API_URL` — base URL for the API (no trailing `/`).

#### 2. JWT secret rotation

- Maintain a primary `JWT_SECRET` and optional `JWT_SECRET_PREVIOUS`.
- Rotate by:
  1. Moving current `JWT_SECRET` → `JWT_SECRET_PREVIOUS`.
  2. Generating a new strong `JWT_SECRET`.
  3. Restarting API.
- Old tokens continue to validate during the grace period via `JWT_SECRET_PREVIOUS`.

#### 3. CORS configuration

- Set `CORS_ORIGINS` to **only** the deployed UI origins.
- Keep `allow_credentials=True` and **do not** use `"*"` with credentials.
- Verify preflight and auth headers work from browser (login, API calls).

#### 4. HTTPS requirement

- Terminate TLS at your ingress / load balancer:
  - Vercel / Netlify / CloudFront / Nginx / Traefik.
- Ensure all external URLs (`NEXT_PUBLIC_API_URL`, OAuth redirects, webhooks) use `https://`.
- Redirect `http` → `https` at the edge where possible.

#### 5. Docker build & deployment

- **Backend**
  - Build image with `docker build -t kirp-api .`.
  - Run via `docker-compose.yml` or your own orchestrator:
    - Expose port `8000`.
    - Mount Prometheus multiproc dir if using metrics.
- **Frontend**
  - Build Next.js app: `npm install && npm run build`.
  - Deploy on Vercel/Netlify or as a static+Node container:
    - Set `NEXT_PUBLIC_API_URL` to the API URL.
    - Configure CORS on the API accordingly.

#### 6. Data & backup strategy

- **MongoDB**
  - Configure replica set or managed cluster.
  - Schedule backups (snapshots or `mongodump`) with retention.
- **Postgres**
  - Use managed service or configure WAL archiving / periodic dumps.
  - Verify restore procedure in a staging environment.
- **Redis**
  - If used for caching / idempotency, decide whether persistence is required.

#### 7. Logging strategy

- Standardize on structured logs from the API:
  - Include `tenant_id`, `space_id`, `user_id`, and trace IDs where available.
  - Send logs to a central system (ELK, Loki, CloudWatch, etc.).
- Ensure sensitive data (passwords, raw tokens) is **never** logged.

#### 8. Monitoring & metrics

- Prometheus exporter is already integrated:
  - Confirm `PROMETHEUS_MULTIPROC_DIR` is set when running multiple workers.
  - Scrape `/metrics` from your Prometheus server.
- Build Grafana dashboards for:
  - Request rate / latency / errors.
  - Mongo / Postgres health.
  - Agent runs, notifications, and history volume.

#### 9. Security review

- Verify:
  - All authenticated routes rely on JWT and tenant context.
  - No cross-tenant access is possible without explicit admin roles.
  - Admin-only endpoints are guarded with `require_role("admin")`.
  - Passwords are hashed with bcrypt and never returned in API responses.

