# KIRP UI — Contributing & Dev Flow

## Running the UI locally

- Dev server (App Router on port 3100):

  ```bash
  npm install
  npm run dev
  # UI: http://localhost:3100
  ```

- Backend API is expected on:

  ```bash
  export NEXT_PUBLIC_API_URL=http://localhost:8000
  ```

## Auth in development

The UI sends a `Bearer` token when `NEXT_PUBLIC_DEV_TOKEN` is set:

```env
NEXT_PUBLIC_DEV_TOKEN=dev-local-token
```

The backend accepts this token when `DEV_TOKEN` matches (and auth is not already skipped via `ENV=development` or `SKIP_AUTH=1`):

```bash
export DEV_TOKEN=dev-local-token
```

This keeps dev auth explicit and avoids accidental 401s.

## TEST_E2E.sh

End-to-end validation script from the repo root:

```bash
./TEST_E2E.sh
```

It checks:

- Core containers and infra (API, DBs, Kafka, Redis, Qdrant, OPA, etc.)
- RAG ingest/query
- Agents, governance, events, and tenants
- UI build, routes, static assets, and env consistency

If the script reports:

- `⚠ NEXT_PUBLIC_DEV_TOKEN missing` — add it to `.env.local` as above.
- `⚠ WebSocket health endpoint not available` — ensure the API is running; the endpoint is `/api/v1/realtime/ws/health`.

## Static assets

The UI exposes:

- `/favicon.ico` — small KIRP icon
- `/icon.svg` — SVG app icon
- `/logo.svg` — logo for docs/marketing
- `/manifest.json` — basic PWA-style manifest

`TEST_E2E.sh` validates these endpoints automatically.

## Common issues

- **`Cannot find module './XXX.js'` in dev**  
  Clear the Next.js build cache:

  ```bash
  rm -rf .next node_modules/.cache
  npm run dev
  ```

- **401 from `/api/events` in dev**  
  - Make sure `ENV=development` or `SKIP_AUTH=1` on the backend, _or_
  - Set matching `DEV_TOKEN` (backend) and `NEXT_PUBLIC_DEV_TOKEN` (UI).

