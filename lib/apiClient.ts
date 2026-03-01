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
import { DEFAULT_TENANT_ID, DEFAULT_USER_ID } from "@/lib/constants";

/** Backend API base URL. Must be set for UI → API requests. */
const BASE =
  (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) ||
  "http://localhost:8000";

const DEV_TOKEN =
  typeof process !== "undefined"
    ? process.env?.NEXT_PUBLIC_DEV_TOKEN ?? ""
    : "";

function getRuntimeToken(): string | null {
  if (typeof window === "undefined") return DEV_TOKEN || null;
  const fromLocal =
    window.localStorage.getItem("access_token") ??
    window.localStorage.getItem("kirp_auth_token") ??
    window.localStorage.getItem("kirp_token");
  const fromSession =
    window.sessionStorage.getItem("access_token") ??
    window.sessionStorage.getItem("kirp_auth_token") ??
    window.sessionStorage.getItem("kirp_token");
  return fromLocal || fromSession || DEV_TOKEN || null;
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const token = getRuntimeToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
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

async function patch<T>(path: string, body?: unknown): Promise<T> {
  const url = buildUrl(path);
  const res = await fetch(url, {
    method: "PATCH",
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

// ---------- LLM Usage ----------

export interface LlmUsageResponse {
  groq: Record<string, unknown>;
  openai: Record<string, unknown>;
  anthropic: Record<string, unknown>;
  gemini: Record<string, unknown>;
  recommendation: string;
}

export async function getLlmUsage(): Promise<LlmUsageResponse> {
  return get<LlmUsageResponse>("/api/v1/llm/usage");
}

// ---------- Ask / Insights ----------

export interface AskResponse {
  answer: string;
  sources: unknown[];
  needs_external_info: boolean;
}

/** Ask API: body is only { query }. Tenant/user/space are derived from JWT on the backend. */
export async function askV1(body: { query: string }): Promise<AskResponse> {
  return post<AskResponse>("/api/v1/ask", body);
}

export interface InsightV1 {
  id: string;
  type: string;
  category: string;
  title: string;
  body: string;
  data: Record<string, unknown>;
  confidence: number;
  source_entities: Array<{ entity: string; id: string; title?: string }>;
  created_at: string;
}

/** Insights; tenant/user from JWT. */
export async function getInsightsV1(params?: {
  space_id?: string;
  limit?: number;
}): Promise<InsightV1[]> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.space_id) q.space_id = params.space_id;
  if (params?.limit != null) q.limit = params.limit;
  const json = await get<InsightV1[]>("/api/v1/insights", q);
  return Array.isArray(json) ? json : [];
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

export interface AgentV1 {
  id: string;
  name: string;
  type: string;
  triggers: string[];
  description: string;
  last_run?: string | null;
  next_run?: string | null;
}

/** List agents; tenant is derived from JWT. */
export async function listAgentsV1(): Promise<AgentV1[]> {
  const json = await get<AgentV1[]>("/api/v1/agents");
  return Array.isArray(json) ? json : [];
}

/** Run agent; tenant/user/space come from JWT. No need to send tenant_id/space_id/user_id in body. */
export async function runAgentV1(
  agentId: string,
  body?: Record<string, unknown>,
): Promise<{ ok: boolean; agent_id: string; result?: Record<string, unknown> }> {
  return post<{ ok: boolean; agent_id: string; result?: Record<string, unknown> }>(
    `/api/v1/agents/${encodeURIComponent(agentId)}/run`,
    body ?? {},
  );
}

export interface AgentLogV1 {
  agent_name: string;
  run_at: string;
  duration_ms: number;
  result_count: number;
  errors: string[];
  tenant_id: string;
  space_id: string;
  trigger: string;
}

/** Agent logs; tenant from JWT. */
export async function getAgentLogsV1(params?: {
  agent_name?: string;
  limit?: number;
}): Promise<AgentLogV1[]> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.agent_name) q.agent_name = params.agent_name;
  if (params?.limit != null) q.limit = params.limit;
  const json = await get<AgentLogV1[]>("/api/v1/agents/logs", q);
  return Array.isArray(json) ? json : [];
}

export interface AgentActionV1 {
  id: string;
  agent: string;
  type: string;
  payload: Record<string, unknown>;
  status: string;
  tenant_id: string;
  space_id: string;
  created_at: string;
  executed_at?: string | null;
  error?: string | null;
}

/** Agent actions; tenant from JWT. */
export async function getAgentActionsV1(params?: {
  status?: string;
  agent?: string;
  limit?: number;
}): Promise<AgentActionV1[]> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.status) q.status = params.status;
  if (params?.agent) q.agent = params.agent;
  if (params?.limit != null) q.limit = params.limit;
  const json = await get<AgentActionV1[]>("/api/v1/agents/actions", q);
  return Array.isArray(json) ? json : [];
}

// ---------- Notifications (Activity Center) ----------

export interface NotificationV1 {
  id: string;
  tenant_id: string;
  space_id: string;
  user_id: string;
  type: string;
  title: string;
  body: string;
  entity_id?: string | null;
  created_at: string;
  read: boolean;
  meta?: Record<string, unknown>;
}

export async function listNotificationsV1(params?: {
  tenant_id?: string;
  user_id?: string;
  limit?: number;
  type?: string;
}): Promise<NotificationV1[]> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  if (params?.limit != null) q.limit = params.limit;
  if (params?.type) q.type = params.type;
  const json = await get<NotificationV1[]>("/api/v1/notifications", q);
  return Array.isArray(json) ? json : [];
}

export async function getUnreadCountV1(params?: { tenant_id?: string; user_id?: string }): Promise<number> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  const res = await get<{ unread_count: number }>("/api/v1/notifications/unread-count", q);
  return typeof res.unread_count === "number" ? res.unread_count : 0;
}

export async function markNotificationReadV1(notificationId: string): Promise<{ ok: boolean }> {
  return post<{ ok: boolean }>(`/api/v1/notifications/${encodeURIComponent(notificationId)}/read`, {});
}

export async function markAllNotificationsReadV1(params?: {
  tenant_id?: string;
  user_id?: string;
}): Promise<{ ok: boolean; marked_count: number }> {
  const q: Record<string, string | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  const url = buildUrl("/api/v1/notifications/read-all", q);
  const res = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...authHeaders() },
  });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<{ ok: boolean; marked_count: number }>;
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

// ---------- V1 domain (history 2.0, signals, visuals, content) ----------

export type HistoryEntryV1 = {
  id: string;
  tenant_id: string;
  space_id: string;
  user_id: string;
  type: string;
  title: string;
  body: string;
  entity_id: string | null;
  source: string;
  created_at: string | null;
  meta: Record<string, unknown>;
};

export async function listHistoryV1(params?: {
  tenant_id?: string;
  user_id?: string;
  limit?: number;
  type?: string;
  from?: string;
  to?: string;
}): Promise<HistoryEntryV1[]> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  if (params?.limit != null) q.limit = params.limit;
  if (params?.type) q.type = params.type;
  if (params?.from) q.from = params.from;
  if (params?.to) q.to = params.to;
  const json = await getJson("/api/v1/history", q);
  return Array.isArray(json) ? (json as HistoryEntryV1[]) : [];
}

/** @deprecated Use listHistoryV1 for History 2.0 timeline. */
export async function listHistory(params?: {
  tenantId?: string;
  spaceId?: string;
  userId?: string;
}): Promise<{ data: HistoryEntryV1[]; meta?: Record<string, unknown> }> {
  const entries = await listHistoryV1({
    tenant_id: params?.tenantId ?? DEFAULT_TENANT_ID,
    user_id: params?.userId,
    limit: 100,
  });
  return { data: entries, meta: {} };
}

// ---------- V1 auth ----------

export type AuthUserV1 = {
  id: string;
  email: string;
  name: string;
  tenant_id: string;
  roles: string[];
};

export type AuthResponseV1 = {
  access_token: string;
  user: AuthUserV1;
};

export async function signupV1(body: {
  email: string;
  password: string;
  name: string;
}): Promise<AuthResponseV1> {
  const json = await post<AuthResponseV1>("/api/v1/auth/signup", body);
  return json;
}

export async function loginV1(body: {
  email: string;
  password: string;
}): Promise<AuthResponseV1> {
  const json = await post<AuthResponseV1>("/api/v1/auth/login", body);
  return json;
}

export async function meV1(): Promise<AuthUserV1> {
  return get<AuthUserV1>("/api/v1/auth/me");
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

// ---------- V1 Tasks (SchemaEngine life objects) ----------

export interface TaskV1 {
  id: string;
  title: string;
  due_date: string | null;
  source: string | null;
  source_event_id: string | null;
  tenant_id: string;
  space_id: string;
  user_id: string | null;
  status: string | null;
}

export async function listTasksV1(params?: {
  tenant_id?: string;
  space_id?: string;
  status?: string;
  limit?: number;
}): Promise<{ data: TaskV1[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id;
  if (params?.status) q.status = params.status;
  if (params?.limit) q.limit = params.limit;
  const json = await getJson("/api/v1/tasks", q);
  const data = Array.isArray((json as { data?: TaskV1[] })?.data) ? (json as { data: TaskV1[] }).data : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

export async function updateNodeV1(
  nodeId: string,
  body: { title?: string; description?: string; status?: string; priority?: string; due_date?: string; parent_id?: string },
  params?: { tenant_id?: string; user_id?: string }
): Promise<{ ok: boolean; node: SchemaNodeV1 }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  const url = `/api/v1/nodes/${encodeURIComponent(nodeId)}?${new URLSearchParams(q).toString()}`;
  return patch(url, body);
}

export async function createTaskV1(
  body: { title: string; due_date?: string; status?: string; priority?: string; description?: string },
  params?: { tenant_id?: string; space_id?: string; user_id?: string }
): Promise<{ ok: boolean; data: TaskV1 }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id ?? "all";
  if (params?.user_id) q.user_id = params.user_id ?? "system";
  const url = `/api/v1/tasks?${new URLSearchParams(q).toString()}`;
  return post(url, body);
}

export async function createNodeV1(
  body: { entity: string; title: string; due_date?: string; status?: string; priority?: string; description?: string; parent_id?: string },
  params?: { tenant_id?: string; space_id?: string; user_id?: string }
): Promise<{ ok: boolean; node: SchemaNodeV1 }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id ?? "all";
  if (params?.user_id) q.user_id = params.user_id ?? "system";
  const url = `/api/v1/nodes?${new URLSearchParams(q).toString()}`;
  return post(url, body);
}

export async function getNodeV1(
  nodeId: string,
  params?: { tenant_id?: string }
): Promise<{ ok: boolean; node: SchemaNodeV1 }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  return get(`/api/v1/nodes/${encodeURIComponent(nodeId)}`, q);
}

// ---------- Reminders (upcoming obligations) ----------

export interface ObligationV1 {
  id: string;
  title: string;
  entity: string;
  due_date: string | null;
  status: string | null;
  tenant_id: string;
  space_id: string;
  metadata?: Record<string, unknown>;
}

export async function getRemindersUpcoming(params?: {
  tenant_id?: string;
  space_id?: string;
  horizon_days?: number;
}): Promise<{ ok: boolean; obligations: ObligationV1[]; due_from?: string; due_to?: string }> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id;
  if (params?.horizon_days != null) q.horizon_days = params.horizon_days;
  return get<{ ok: boolean; obligations: ObligationV1[]; due_from?: string; due_to?: string }>(
    "/api/v1/reminders/upcoming",
    q,
  );
}

// ---------- Context (accessible spaces for Second Brain) ----------

export async function getContextAccessibleSpaces(
  tenantId: string,
  userId: string,
): Promise<{ tenant_id: string; user_id: string; space_ids: string[] }> {
  return get("/api/v1/context/accessible-spaces", { tenant_id: tenantId, user_id: userId });
}

export async function getContextSpaces(
  tenantId: string,
  userId: string,
): Promise<{ tenant_id: string; user_id: string; spaces: { space_id: string; role: string | null }[] }> {
  return get("/api/v1/context/spaces", { tenant_id: tenantId, user_id: userId });
}

// ---------- Schema nodes (life areas, commitments, tasks, projects) ----------

export interface SchemaNodeV1 {
  id: string;
  tenant_id: string;
  space_id: string;
  entity: string;
  title: string;
  description?: string | null;
  parent_id?: string | null;
  status?: string | null;
  priority?: string | null;
  due_date?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
}

export async function listNodesV1(params?: {
  tenant_id?: string;
  space_id?: string;
  entity?: string;
  status?: string;
  limit?: number;
}): Promise<{ data: SchemaNodeV1[]; meta?: Record<string, unknown> }> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id;
  if (params?.entity) q.entity = params.entity;
  if (params?.status) q.status = params.status;
  if (params?.limit) q.limit = params.limit;
  const json = await getJson("/api/v1/nodes", q);
  const data = Array.isArray((json as { data?: SchemaNodeV1[] })?.data)
    ? (json as { data: SchemaNodeV1[] }).data
    : [];
  return { data, meta: (json as { meta?: Record<string, unknown> })?.meta ?? {} };
}

// ---------- Graph ----------

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

// ---------- V1 Graph (Life Graph: schema + events) ----------

export interface GraphNodeV1 {
  id: string;
  type: string;
  label: string;
  meta?: Record<string, unknown>;
}

export interface GraphEdgeV1 {
  source: string;
  target: string;
  type: string;
  meta?: Record<string, unknown>;
}

export interface GraphV1Response {
  nodes: GraphNodeV1[];
  edges: GraphEdgeV1[];
  stats?: { node_count: number; edge_count: number };
}

export async function getGraphV1(params?: {
  tenant_id?: string;
  space_id?: string;
  life_area?: string;
  project_id?: string;
  date_from?: string;
  date_to?: string;
  entity_types?: string;
  source?: string;
  limit_nodes?: number;
}): Promise<GraphV1Response> {
  const q: Record<string, string | number | undefined> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id;
  if (params?.life_area) q.life_area = params.life_area;
  if (params?.project_id) q.project_id = params.project_id;
  if (params?.date_from) q.date_from = params.date_from;
  if (params?.date_to) q.date_to = params.date_to;
  if (params?.entity_types) q.entity_types = params.entity_types;
  if (params?.source) q.source = params.source;
  if (params?.limit_nodes != null) q.limit_nodes = params.limit_nodes;
  const json = await getJson("/api/v1/graph", q);
  const j = json as GraphV1Response;
  return {
    nodes: Array.isArray(j.nodes) ? j.nodes : [],
    edges: Array.isArray(j.edges) ? j.edges : [],
    stats: j.stats,
  };
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

// ---------- M3 IdentityOS ----------

export interface M3Reflection {
  id: string;
  reflection_date: string;
  reflection_text: string;
  pillar_scores: Record<string, number>;
  mood: string;
}

/** Semantic search hit from GET /m3/reflections?q=... */
export interface M3ReflectionSearchHit {
  event_id?: string;
  content: string;
  score?: number;
  source?: string;
  metadata?: Record<string, unknown>;
}

export interface M3ReflectionsResponse {
  data: M3Reflection[] | M3ReflectionSearchHit[];
  meta: { count: number; search?: boolean; query?: string };
}

export interface M3Kpis {
  data: {
    daily_reflection_completion: {
      days_with_reflection: number;
      total_reflections: number;
      target_met_days: number;
      window_days: number;
      explanation: string;
    };
    recall_retention: {
      completed_or_snoozed_count: number;
      total_actions: number;
      rate_pct: number;
      explanation: string;
    };
    identity_alignment: { has_profile: boolean; pillar_scores: Record<string, number>; explanation: string };
    gap_closure: { value: number | null; snapshot_count: number; explanation: string };
  };
  meta: { tenant_id: string; user_id: string; window_days: number };
}

export async function m3Reflect(body: {
  reflection_text: string;
  pillar_scores?: Record<string, number>;
  mood?: string;
  reflection_date?: string;
}): Promise<{ ok: boolean; event_id: string }> {
  return post<{ ok: boolean; event_id: string }>("/api/v1/m3/reflect", body);
}

export async function m3ListReflections(params?: {
  limit?: number;
  q?: string;
  since?: string;
  until?: string;
}): Promise<M3ReflectionsResponse> {
  const p: Record<string, string | number | undefined> = {};
  if (params?.limit != null) p.limit = params.limit;
  if (params?.q != null && params.q.trim() !== "") p.q = params.q.trim();
  if (params?.since != null && params.since.trim() !== "") p.since = params.since.trim();
  if (params?.until != null && params.until.trim() !== "") p.until = params.until.trim();
  return get<M3ReflectionsResponse>("/api/v1/m3/reflections", p);
}

export interface M3MicroAction {
  action_id: string;
  title: string;
  pillar: string;
  status: string;
  due_by: string | null;
  roi_score: number;
  completed_at: string | null;
  feedback: string;
}

export interface M3Synthesis {
  synthesis_id: string;
  week_start: string;
  week_end: string;
  summary: string;
  pillar_trends: Record<string, unknown>;
  insights: string[];
  created_at: string | null;
}

export interface M3Evolution {
  evolution_id: string;
  month: string;
  trajectory: unknown[];
  new_goals: string[];
  pillar_shifts: Record<string, unknown>;
  created_at: string | null;
}

export async function m3ListActions(params?: {
  status?: string;
  limit?: number;
}): Promise<{ data: M3MicroAction[]; meta: { count: number } }> {
  const p: Record<string, string | number | undefined> = {};
  if (params?.status != null) p.status = params.status;
  if (params?.limit != null) p.limit = params.limit;
  return get<{ data: M3MicroAction[]; meta: { count: number } }>("/api/v1/m3/actions", p);
}

export async function m3ListSynthesis(params?: { limit?: number }): Promise<{
  data: M3Synthesis[];
  meta: { count: number };
}> {
  return get<{ data: M3Synthesis[]; meta: { count: number } }>(
    "/api/v1/m3/synthesis",
    params ? { limit: params.limit } : undefined,
  );
}

export async function m3ListEvolution(params?: { limit?: number }): Promise<{
  data: M3Evolution[];
  meta: { count: number };
}> {
  return get<{ data: M3Evolution[]; meta: { count: number } }>(
    "/api/v1/m3/evolution",
    params ? { limit: params.limit } : undefined,
  );
}

export async function m3GetKpis(params?: { days?: number }): Promise<M3Kpis> {
  return get<M3Kpis>("/api/v1/m3/kpis", params as Record<string, number>);
}

export async function m3Health(): Promise<{ module: string; event_types_registered: number; agents_registered: number }> {
  return get("/api/v1/m3/health");
}

export async function m3SynthesisRequest(body?: { week_start?: string; week_end?: string }): Promise<{ ok: boolean; event_id: string }> {
  return post<{ ok: boolean; event_id: string }>("/api/v1/m3/synthesis", body ?? {});
}

export async function m3EvolutionRequest(body?: { month?: string }): Promise<{ ok: boolean; event_id: string }> {
  return post<{ ok: boolean; event_id: string }>("/api/v1/m3/evolution", body ?? {});
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

// ---------- Agent run ----------

export async function runAgent(
  agentId: string,
  body?: { tenant_id?: string; space_id?: string; user_id?: string;[key: string]: unknown },
): Promise<Record<string, unknown>> {
  return post<Record<string, unknown>>(`/api/agents/${encodeURIComponent(agentId)}/run`, body ?? {});
}

// ---------- Aggregated export ----------

export const apiClient = {
  getObservabilityHealth,
  getMetricsSnapshot,
  getStats,
  getLlmUsage,
  askV1,
  getInsightsV1,
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
  listHistoryV1,
  listSignals,
  listVisuals,
  listContentIntelligence,
  getGraph,
  getGraphV1,
  ingestV1,
  queryV1,
  runAgent,
  listAgentsV1,
  runAgentV1,
  getAgentLogsV1,
  getAgentActionsV1,
  listNotificationsV1,
  getUnreadCountV1,
  markNotificationReadV1,
  markAllNotificationsReadV1,
  listTasksV1,
  getRemindersUpcoming,
  getContextAccessibleSpaces,
  getContextSpaces,
  listNodesV1,
  updateNodeV1,
  createTaskV1,
  createNodeV1,
  getNodeV1,
  listConnections,
  connectIntegration,
  disconnectIntegration,
  syncConnection,
  validateConnection,
  getConnectionErrors,
  getConnectionsOAuthStartUrl,
  signupV1,
  loginV1,
  meV1,
  m3Reflect,
  m3ListReflections,
  m3ListActions,
  m3ListSynthesis,
  m3ListEvolution,
  m3GetKpis,
  m3Health,
  m3SynthesisRequest,
  m3EvolutionRequest,
};

// ---------- Connections Hub ----------

export interface ConnectorStatus {
  integration: string;
  label: string;
  status: "connected" | "not_connected" | "error";
  connected: boolean;
  last_sync_at: string | null;
  last_sync_status: string;
  last_sync_result: Record<string, unknown>;
  error_count: number;
}

export async function listConnections(params?: {
  tenant_id?: string;
  user_id?: string;
}): Promise<{ ok: boolean; connectors: ConnectorStatus[] }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  return get("/api/v1/connections", q);
}

export async function connectIntegration(
  integration: string,
  body: { access_token?: string; refresh_token?: string; extra?: Record<string, unknown> },
  params?: { tenant_id?: string; user_id?: string }
): Promise<{ ok: boolean }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  const url = `/api/v1/connections/${encodeURIComponent(integration)}/connect?${new URLSearchParams(q).toString()}`;
  return post(url, body);
}

export async function disconnectIntegration(
  integration: string,
  params?: { tenant_id?: string; user_id?: string }
): Promise<{ ok: boolean; disconnected: boolean }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  const url = `/api/v1/connections/${encodeURIComponent(integration)}/disconnect?${new URLSearchParams(q).toString()}`;
  return post(url);
}

export async function syncConnection(
  integration: string,
  params?: { tenant_id?: string; space_id?: string; user_id?: string }
): Promise<{ ok: boolean; result: Record<string, unknown> }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.space_id) q.space_id = params.space_id ?? "all";
  if (params?.user_id) q.user_id = params.user_id ?? "system";
  const url = `/api/v1/connections/${encodeURIComponent(integration)}/sync?${new URLSearchParams(q).toString()}`;
  return post(url);
}

export async function validateConnection(
  integration: string,
  params?: { tenant_id?: string; user_id?: string }
): Promise<{ ok: boolean; valid: boolean; reason?: string }> {
  const q: Record<string, string> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  return get(`/api/v1/connections/${encodeURIComponent(integration)}/validate`, q);
}

export async function getConnectionErrors(
  integration: string,
  params?: { tenant_id?: string; user_id?: string; limit?: number }
): Promise<{ ok: boolean; errors: { at: string; message: string }[] }> {
  const q: Record<string, string | number> = {};
  if (params?.tenant_id) q.tenant_id = params.tenant_id;
  if (params?.user_id) q.user_id = params.user_id;
  if (params?.limit) q.limit = params.limit;
  return get(`/api/v1/connections/${encodeURIComponent(integration)}/errors`, q);
}

/** WebSocket URL for notifications (derived from NEXT_PUBLIC_API_URL). */
export function getNotificationsWsUrl(): string {
  const base = (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) || "http://localhost:8000";
  const wsBase = base.replace(/^http/, "ws");
  return `${wsBase.replace(/\/$/, "")}/ws/notifications`;
}

/** Base URL for API (for OAuth redirects). */
export function getConnectionsOAuthStartUrl(
  integration: "gmail" | "calendar" | "slack" | "notion",
  params?: { tenant_id?: string; user_id?: string }
): string {
  const base = (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) || "http://localhost:8000";
  const p = new URLSearchParams();
  if (params?.tenant_id) p.set("tenant_id", params.tenant_id);
  if (params?.user_id) p.set("user_id", params.user_id);
  return `${base.replace(/\/$/, "")}/api/v1/connections/oauth/${integration}/start?${p.toString()}`;
}
