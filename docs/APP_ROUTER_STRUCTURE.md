# Next.js App Router — Structure and Static Assets

## Route tree (correct architecture)

```
app/
├── layout.tsx              ← ROOT LAYOUT (required; single root)
├── page.tsx                 ← route: /
├── loading.tsx              ← root loading UI
├── globals.css
├── login/page.tsx            ← /login
├── logout/page.tsx          ← /logout
├── signup/page.tsx           ← /signup
├── (dashboard)/             ← ROUTE GROUP (no URL segment)
│   ├── layout.tsx           ← dashboard shell (AppShell) for all children
│   ├── loading.tsx          ← loading UI for dashboard segment
│   ├── dashboard/page.tsx   ← /dashboard
│   ├── tasks/page.tsx       ← /tasks
│   ├── agents/page.tsx     ← /agents
│   └── ...                  ← all other dashboard routes
└── api/                     ← API routes (not layouts)
    └── ...
```

## Design decisions

1. **Single root layout**  
   Only `app/layout.tsx` wraps the whole app. It provides `<html>`, `<body>`, theme, and global UI. There is no other root-level layout.

2. **`(dashboard)` is a route group**  
   The parentheses mean it does **not** add a URL segment. So:
   - `app/page.tsx` → `/`
   - `app/(dashboard)/dashboard/page.tsx` → `/dashboard`
   - `app/(dashboard)/tasks/page.tsx` → `/tasks`  
   There is no `app/(dashboard)/page.tsx`, so `/` is only handled by `app/page.tsx` (redirect to `/dashboard`). No duplicate route.

3. **Two layouts, no conflict**  
   - **Root layout** (`app/layout.tsx`): wraps every route; required by Next.js.
   - **Dashboard layout** (`app/(dashboard)/layout.tsx`): wraps only routes under `(dashboard)` (e.g. `/dashboard`, `/tasks`). Auth routes (`/login`, `/signup`, `/logout`) use only the root layout, so they do not get the AppShell sidebar.

4. **Loading boundaries**  
   - `app/loading.tsx`: shown while the root segment is loading.
   - `app/(dashboard)/loading.tsx`: shown while a dashboard child is loading (inside AppShell).  
   This gives a stable shell and avoids layout shift; it does not fix static asset 404s by itself.

## Static assets (`/_next/static/...` 404)

- Next.js serves `/_next/static/*` from the build output (or from memory in `next dev`).
- **If you see 404 for `/_next/static/...`:**
  1. **Dev:** Run `npm run dev` from the project root so `.next` is created and served.
  2. **Production with `output: "standalone"`:** After `next build`, static files and `public` must be copied into the standalone output directory; the server must serve `/_next/static` from there. See [Next.js standalone output](https://nextjs.org/docs/advanced-features/output-file-tracing).
  3. **Reverse proxy:** Ensure `/_next` (and `/static`) are forwarded to the Next.js server, not served by the proxy.
  4. **Clean build:** Run `rm -rf .next && npm run build` so a full build completes and `.next/static` is populated (build must pass lint/type-check for a full success).

This app structure does not cause static 404 by itself; the cause is usually build output, deployment, or proxy configuration.
