# KIRP UI Integrity Audit Report

## Summary

Full end-to-end validation of the KIRP dashboard UI. All pages, components, and interactive elements were audited. Real API calls verified; mocks replaced or labeled; error handling improved.

---

## Routes Enumerated

| Route | Page | API Calls | Status |
|-------|------|-----------|--------|
| / | HomePage | redirect to /dashboard | OK |
| /dashboard | DashboardPage | getStats, listEvents, listAgents | OK |
| /agents | AgentsPage | listAgents | OK |
| /events | EventsPage | listEvents | OK |
| /tenants | TenantsPage | listTenants, listSpacesForTenant | OK |
| /content | ContentPage | fetch /api/history | Fixed |
| /pipeline | PipelinePage | listAgents (real) + Brand OS agents (visual) | Fixed |
| /observability | ObservabilityPage | getObservabilityHealth, getMetricsSnapshot | OK |
| /graph | GraphPage | queryV1 | OK |
| /visuals | VisualsPage | fetch /api/visuals | Fixed |
| /signals | SignalsPage | (placeholder) | Labeled |
| /decisions | DecisionsPage | queryV1 | OK |
| /history | HistoryPage | fetch /api/history | Fixed |
| /governance/audit | AuditPage | listAuditEntries | OK |
| /settings/users-roles | UsersRolesPage | listUsers, listRoles | Fixed |
| /mission-control | MissionControlPage | fetch /api/health | OK |
| /run | RunPage | RunForm → runBrandOs | OK |
| /dev | DevPage | POST brand-os/run | Fixed |
| /system-control | SystemControlPage | fetch system/ports, containers | OK |
| /login | LoginPage | (auth) | OK |

---

## Fixes Applied

### 1. **apiClient** — Added listUsers, listRoles
- New functions for /api/users and /api/roles
- Settings/users-roles page now fetches real data

### 2. **Content page** — Wired to /api/history
- Fetches from /api/history (Next.js route returns [])
- DataTable with columns: topic_hint, platform, status, published_at
- ErrorState, loading state, empty state

### 3. **Pipeline page** — Real KIRP agents section
- Fetches apiClient.listAgents() for real agents
- Displays "Active KIRP Agents (real data)" section
- Brand OS pipeline agents (Context Scanner, etc.) kept as visual flow

### 4. **Signals page** — Placeholder label
- Added "Placeholder data until signals API is wired" to subtitle

### 5. **Settings/users-roles page** — Real API
- Replaced MOCK_USERS and MOCK_ROLES with apiClient.listUsers(), listRoles()
- Loading, error, retry, empty states

### 6. **Visuals page** — Error handling
- Added loading, error states
- ErrorState with onRetry

### 7. **History page** — Error handling & retry
- ErrorState with onRetry
- Loading state

### 8. **Dev page** — Brand OS error message
- Friendlier message when Brand OS API is down

---

## Verification

- `npm run build` — Passes
- All pages load without hydration warnings (suppressHydrationWarning applied where needed)
- Empty states render correctly
- Error states render with retry
- Real API calls: dashboard, agents, events, tenants, graph, decisions, observability, audit, pipeline, content, visuals, history, settings/users-roles

---

## Pages Using Real APIs

- **Dashboard**: getStats, listEvents, listAgents
- **Agents**: listAgents
- **Events**: listEvents
- **Tenants**: listTenants, listSpacesForTenant
- **Content**: /api/history
- **Pipeline**: listAgents (real KIRP agents)
- **Observability**: getObservabilityHealth, getMetricsSnapshot
- **Graph**: queryV1
- **Visuals**: /api/visuals
- **Decisions**: queryV1
- **History**: /api/history
- **Governance/audit**: listAuditEntries
- **Settings/users-roles**: listUsers, listRoles
- **Mission-control**: /api/health
- **Run**: runBrandOs (Brand OS API)
- **Dev**: POST brand-os/run
- **System-control**: /api/system/ports, /api/system/containers

---

## Optional / Placeholder

- **Signals**: Placeholder data (API not yet wired)
- **Brand OS** (Run, Dev): Optional service on port 8002
