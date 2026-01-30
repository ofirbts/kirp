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

const BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "";

function buildUrl(
  path: string,
  params?: Record<string, string | number | undefined>,
): string {
  const url = new URL(path, BASE || "http://localhost:8000");
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
  const res = await fetch(url, { credentials: "include" });
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

async function post<T>(path: string, body?: unknown): Promise<T> {
  const url = buildUrl(path);
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  return get<ListEventsResponse>("/api/events", q);
}

// ---------- Governance & Audit ----------

export async function listPolicies(): Promise<ListPoliciesResponse> {
  return get<ListPoliciesResponse>("/api/policies");
}

export async function listAuditEntries(): Promise<ListAuditResponse> {
  return get<ListAuditResponse>("/api/audit");
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
  listPolicies,
  listAuditEntries,
  ingestV1,
  queryV1,
};
