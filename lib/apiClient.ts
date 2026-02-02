/**
 * KIRP API client — minimal surface for the new Next.js dashboard.
 * Base URL: NEXT_PUBLIC_API_URL (e.g. http://localhost:8000).
 */

import type {
  EventFilter,
  ListEventsResponse,
  ListAgentsResponse,
  ListTenantsResponse,
  ListSpacesResponse,
  ListPoliciesResponse,
  ListAuditResponse,
} from "@/lib/types";

const TENANT = "default";
const SPACE = "all";

/** Backend API base URL. Must be set for UI → API requests. */
const BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

const DEV_TOKEN =
  typeof process !== "undefined"
    ? process.env?.NEXT_PUBLIC_DEV_TOKEN ?? ""
    : "";

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (DEV_TOKEN) {
    headers["Authorization"] = `Bearer ${DEV_TOKEN}`;
  }
  return headers;
}

function buildUrl(
  path: string,
  params?: Record<string, string | number | undefined>,
): string {
  const base = BASE;
  const url = new URL(path, base);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") {
        url.searchParams.set(k, String(v));
      }
    });
  }
  return url.toString();
}

async function get<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<T> {
  const url = buildUrl(path, params);
  const res = await fetch(url, {
    credentials: "include",
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      res.status === 502
        ? `Backend unreachable: ${url}`
        : `${res.status}: ${text || res.statusText}`,
    );
  }
  return res.json() as Promise<T>;
}

/** Fetch raw JSON (for list endpoints that may return array or { data, meta }). */
async function getJson(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<unknown> {
  const url = buildUrl(path, params);
  const res = await fetch(url, {
    credentials: "include",
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(
      res.status === 502
        ? `Backend unreachable: ${url}`
        : `${res.status}: ${text || res.statusText}`,
    );
  }
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const url = buildUrl(path);
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    credentials: "include",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ---------- Observability ----------

export async function getObservabilityHealth(): Promise<Record<string, unknown>> {
  return get<Record<string, unknown>>("/observability/health");
}

export async function getMetricsSnapshot(): Promise<Record<string, unknown>> {
  return get<Record<string, unknown>>("/observability/metrics/snapshot");
}

export async function getStats(): Promise<Record<string, unknown>> {
  return get<Record<string, unknown>>("/api/v1/stats");
}

// ---------- Tenants ----------

export async function listTenants(): Promise<ListTenantsResponse> {
  return get<ListTenantsResponse>("/api/tenants");
}

export async function listSpacesForTenant(
  tenantId: string,
): Promise<ListSpacesResponse> {
  return get<ListSpacesResponse>(
    `/api/tenants/${encodeURIComponent(tenantId)}/spaces`,
  );
}

// ---------- Agents ----------

export async function listAgents(params?: {
  tenantId?: string;
  spaceId?: string;
  status?: string;
  type?: string;
}): Promise<ListAgentsResponse> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  if (params?.status) q.status = params.status;
  if (params?.type) q.type = params.type;
  return get<ListAgentsResponse>("/api/agents", q);
}

// ---------- Events ----------

export async function listEvents(
  filters: EventFilter = {},
): Promise<ListEventsResponse> {
  const q: Record<string, string | undefined> = {};
  if (filters.topic) q.topic = filters.topic;
  if (filters.severity) q.severity = filters.severity;
  if (filters.agentId) q.agentId = filters.agentId;
  if (filters.tenantId) q.tenantId = filters.tenantId;
  if (filters.spaceId) q.spaceId = filters.spaceId;
  if (filters.status) q.status = filters.status;
  if (filters.from) q.from = filters.from;
  if (filters.to) q.to = filters.to;
  const json = await getJson("/api/events", q);
  const data = Array.isArray(json) ? json : (json as { data?: unknown[] })?.data ?? [];
  return { data, meta: (json && typeof json === "object" && "meta" in json ? (json as { meta: Record<string, unknown> }).meta : {}) ?? {} };
}

// ---------- Users & Roles ----------

export async function listUsers(): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  return get<{ data: unknown[]; meta?: Record<string, unknown> }>("/api/users");
}

export async function listRoles(): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  return get<{ data: unknown[]; meta?: Record<string, unknown> }>("/api/roles");
}

// ---------- Governance & Audit ----------

export async function listPolicies(): Promise<ListPoliciesResponse> {
  return get<ListPoliciesResponse>("/api/policies");
}

export async function listAuditEntries(): Promise<ListAuditResponse> {
  return get<ListAuditResponse>("/api/audit");
}

// ---------- Decisions ----------

export async function listDecisions(params?: {
  tenantId?: string;
  spaceId?: string;
  agentId?: string;
  from?: string;
  to?: string;
}): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  if (params?.agentId) q.agentId = params.agentId;
  if (params?.from) q.from = params.from;
  if (params?.to) q.to = params.to;
  const json = await getJson("/api/decisions", q);
  const data = Array.isArray((json as { data?: unknown[] })?.data) ? (json as { data: unknown[] }).data : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

// ---------- V1 domain (history, signals, visuals, content) ----------

export async function listHistory(params?: {
  tenantId?: string;
  spaceId?: string;
}): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  const json = await getJson("/api/v1/history", q);
  const data = Array.isArray((json as { data?: unknown[] })?.data) ? (json as { data: unknown[] }).data : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

export async function listSignals(params?: {
  tenantId?: string;
  spaceId?: string;
}): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  const json = await getJson("/api/v1/signals", q);
  const data = Array.isArray((json as { data?: unknown[] })?.data) ? (json as { data: unknown[] }).data : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

export async function listVisuals(params?: {
  tenantId?: string;
  spaceId?: string;
}): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  const json = await getJson("/api/v1/visuals", q);
  const data = Array.isArray((json as { data?: unknown[] })?.data) ? (json as { data: unknown[] }).data : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

export async function listContentIntelligence(params?: {
  tenantId?: string;
  spaceId?: string;
}): Promise<{ data: unknown[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  const json = await getJson("/api/v1/content/intelligence", q);
  const data = Array.isArray((json as { data?: unknown[] })?.data) ? (json as { data: unknown[] }).data : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

export async function getGraph(params?: {
  tenantId?: string;
  spaceId?: string;
  nodeType?: string;
  from?: string;
  to?: string;
}): Promise<{ data: { nodes: unknown[]; edges: unknown[] }; meta?: Record<string, unknown> }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenantId) q.tenantId = params.tenantId;
  if (params?.spaceId) q.spaceId = params.spaceId;
  if (params?.nodeType) q.nodeType = params.nodeType;
  if (params?.from) q.from = params.from;
  if (params?.to) q.to = params.to;
  const json = await getJson("/api/graph", q);
  const data = (json as { data?: { nodes?: unknown[]; edges?: unknown[] } })?.data ?? { nodes: [], edges: [] };
  return { data: { nodes: data.nodes ?? [], edges: data.edges ?? [] }, meta: (json as { meta?: Record<string, unknown> })?.meta };
}

// ---------- RAG pipeline ----------

export async function ingestV1(body: {
  tenant_id: string;
  space_id: string;
  user_id: string;
  content: string;
  source?: string;
}): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>("/api/v1/ingest", body);
}

export async function queryV1(body: {
  tenant_id: string;
  space_id: string;
  user_id: string;
  query: string;
  k?: number;
}): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>("/api/v1/query", body);
}

// ---------- Aggregated export ----------

export const apiClient = {
  getObservabilityHealth,
  getMetricsSnapshot,
  getStats,
  listTenants,
  listSpacesForTenant,
  listAgents,
  listEvents,
  listUsers,
  listRoles,
  listPolicies,
  listAuditEntries,
  listDecisions,
  listHistory,
  listSignals,
  listVisuals,
  listContentIntelligence,
  getGraph,
  ingestV1,
  queryV1,
};
