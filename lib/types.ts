// Core domain types for KIRP Intelligence OS (V1)
// ------------------------------------------------
// NOTE: This file is intentionally implementation-agnostic and mirrors
// the frozen V1 conceptual model (8 primitives + related value types).

export type ID = string;
export type ISO8601 = string;

// ---------- Shared status/value types ----------

export type HealthStatus = "healthy" | "degraded" | "down" | "unknown";

export type EventSeverity = "debug" | "info" | "warning" | "error" | "critical";

export type AgentType =
  | "retrieval"
  | "planner"
  | "executor"
  | "governance"
  | "self_improvement"
  | "routing"
  | "other";

export type AgentStatus = "active" | "paused" | "error";

export type WorkflowStatus = "active" | "paused" | "draft";

export type WorkflowRunStatus = "running" | "success" | "failed" | "cancelled";

export type TaskStatus = "queued" | "running" | "success" | "failed" | "retrying";

// ---------- Tenancy ----------

export interface Tenant {
  id: ID;
  name: string;
  slug: string;
  createdAt: ISO8601;
  updatedAt: ISO8601;
}

export interface Space {
  id: ID;
  tenantId: ID;
  name: string;
  slug: string;
  createdAt: ISO8601;
  updatedAt: ISO8601;
}

// ---------- Identity & Access ----------

export interface User {
  id: ID;
  email: string;
  name: string;
  status: "active" | "disabled" | "invited";
  roles: ID[]; // Role IDs
  tenants: ID[];
  spaces: ID[];
  createdAt: ISO8601;
  lastLoginAt?: ISO8601;
}

export interface Permission {
  resource: string; // e.g. "agents", "decisions", "workflows"
  action: string; // e.g. "read", "write", "execute"
  scope: "tenant" | "space" | "global";
}

export interface Role {
  id: ID;
  name: string;
  description?: string;
  inheritedRoleIds?: ID[];
  permissions: Permission[];
}

// ---------- Governance & Audit ----------

export interface Policy {
  id: ID;
  name: string;
  description?: string;
  engine: "opa";
  source: string; // e.g. Rego source
  createdAt: ISO8601;
  updatedAt: ISO8601;
}

export interface AuditEntry {
  id: ID;
  timestamp: ISO8601;
  actorType: "user" | "agent" | "system";
  actorId: ID;
  tenantId: ID;
  spaceId?: ID;
  action: string; // e.g. "agent.run", "workflow.trigger"
  resourceType: string; // e.g. "Agent", "Decision", "Workflow"
  resourceId?: ID;
  metadata: Record<string, unknown>;
  result: "success" | "failure";
}

// ---------- Agents ----------

export interface AgentMetricSnapshot {
  timestamp: ISO8601;
  successRate: number; // 0..1
  avgLatencyMs: number;
  errorRate: number; // 0..1
  invocations: number;
}

export interface Agent {
  id: ID;
  name: string;
  type: AgentType;
  status: AgentStatus;
  ownerUserId?: ID;
  description?: string;
  lastRunAt?: ISO8601;
  tenantId: ID;
  spaceId?: ID;
  connectedWorkflowIds: ID[]; // n8n workflows
  triggers: string[]; // e.g. ["event:kafka:topicA", "schedule:0 8 * * *"]
  config: Record<string, unknown>;
  metrics: AgentMetricSnapshot[];
}

// ---------- Events ----------

export interface Event {
  id: ID;
  timestamp: ISO8601;
  topic: string;
  key?: string;
  tenantId: ID;
  spaceId?: ID;
  agentId?: ID;
  severity: EventSeverity;
  payloadPreview: string;
  payload: unknown;
  source: "kafka" | "api" | "worker" | "system";
  status?: "processed" | "pending" | "failed" | "dlq";
}

export interface EventFilter {
  topic?: string;
  severity?: EventSeverity;
  agentId?: ID;
  tenantId?: ID;
  spaceId?: ID;
  status?: string;
  from?: ISO8601;
  to?: ISO8601;
}

// ---------- Decisions ----------

export interface DecisionInputRef {
  type: "event" | "document" | "memory" | "agent" | "workflow";
  id: ID;
}

export interface DecisionTraceStep {
  id: ID;
  timestamp: ISO8601;
  agentId?: ID;
  description: string;
  inputSummary: string;
  outputSummary: string;
  raw?: unknown;
}

export interface Decision {
  id: ID;
  createdAt: ISO8601;
  tenantId: ID;
  spaceId?: ID;
  agentId: ID;
  workflowId?: ID;
  inputs: DecisionInputRef[];
  trace: DecisionTraceStep[];
  output: unknown;
  confidence: number; // 0..1
  status: "pending" | "completed" | "error";
  errorMessage?: string;
}

export interface ListDecisionsParams {
  agentId?: ID;
  tenantId?: ID;
  spaceId?: ID;
  from?: ISO8601;
  to?: ISO8601;
}

// ---------- Workflows ----------

export interface Workflow {
  id: ID;
  name: string;
  description?: string;
  status: WorkflowStatus;
  ownerUserId?: ID;
  connectedAgentIds: ID[];
  triggers: string[]; // e.g. "event:topic", "schedule:cron", "manual"
  lastRunAt?: ISO8601;
}

export interface WorkflowRun {
  id: ID;
  workflowId: ID;
  startedAt: ISO8601;
  finishedAt?: ISO8601;
  status: WorkflowRunStatus;
  triggeredBy: "event" | "schedule" | "manual";
  triggerRef?: ID;
  input: unknown;
  output?: unknown;
  logs: string[];
}

export interface WorkflowRunFilter {
  status?: WorkflowRunStatus;
  from?: ISO8601;
  to?: ISO8601;
}

// ---------- Tasks (workers) ----------

export interface Task {
  id: ID;
  queue: string;
  workerId?: string;
  status: TaskStatus;
  createdAt: ISO8601;
  startedAt?: ISO8601;
  finishedAt?: ISO8601;
  attempts: number;
  maxAttempts: number;
  payload: unknown;
  result?: unknown;
  error?: string;
  logs?: string[];
}

export interface TaskFilter {
  queue?: string;
  status?: TaskStatus;
  from?: ISO8601;
  to?: ISO8601;
}

// ---------- Collections / Documents / Vectors ----------

export interface Collection {
  id: ID;
  name: string;
  description?: string;
  vectorSize: number;
  metadataSchema?: Record<string, string>;
}

export interface Document {
  id: ID;
  collectionId: ID;
  tenantId: ID;
  spaceId?: ID;
  title: string;
  contentPreview: string;
  metadata: Record<string, unknown>;
  createdAt: ISO8601;
  updatedAt: ISO8601;
}

export interface VectorQuery {
  vector: number[];
  topK: number;
  filter?: Record<string, unknown>;
}

export interface VectorSearchResult {
  documentId: ID;
  score: number;
  metadata: Record<string, unknown>;
}

// ---------- Knowledge Graph ----------

export type GraphNodeType =
  | "agent"
  | "event"
  | "decision"
  | "workflow"
  | "document"
  | "tenant"
  | "space";

export interface GraphNode {
  id: ID;
  type: GraphNodeType;
  label: string;
  tenantId: ID;
  spaceId?: ID;
  metadata: Record<string, unknown>;
}

export interface GraphEdge {
  id: ID;
  fromId: ID;
  toId: ID;
  type: string; // e.g. "used_document", "triggered_workflow"
  metadata: Record<string, unknown>;
}

// ---------- API response envelopes ----------

export interface ApiListResponse<T> {
  data: T[];
  meta?: Record<string, unknown>;
}

export interface ApiItemResponse<T> {
  data: T;
  meta?: Record<string, unknown>;
}

// ---------- Agent-related request/response types ----------

export interface ListAgentsParams {
  tenantId?: ID;
  spaceId?: ID;
  status?: AgentStatus;
  type?: AgentType;
}

export interface ListAgentsResponse extends ApiListResponse<Agent> { }

export interface GetAgentResponse extends ApiItemResponse<Agent> { }

export interface RunAgentRequest {
  input: unknown;
  tenantId: ID;
  spaceId?: ID;
  context?: Record<string, unknown>;
}

export interface RunAgentResponseData {
  decisionId: ID;
  status: "queued" | "running" | "completed" | "error";
}

export interface RunAgentResponse extends ApiItemResponse<RunAgentResponseData> { }

// ---------- Events ----------

export interface ListEventsResponse extends ApiListResponse<Event> { }

// ---------- Workflows ----------

export interface ListWorkflowsResponse extends ApiListResponse<Workflow> { }

export interface GetWorkflowResponse extends ApiItemResponse<Workflow> { }

export interface TriggerWorkflowRequest {
  input: Record<string, unknown>;
  tenantId: ID;
  spaceId?: ID;
}

export interface TriggerWorkflowResponseData {
  runId: ID;
  status: WorkflowRunStatus;
}

export interface TriggerWorkflowResponse
  extends ApiItemResponse<TriggerWorkflowResponseData> { }

export interface ListWorkflowRunsResponse extends ApiListResponse<WorkflowRun> { }

// ---------- Tasks ----------

export interface ListTasksResponse extends ApiListResponse<Task> { }

export interface GetTaskResponse extends ApiItemResponse<Task> { }

// ---------- Decisions ----------

export interface GetDecisionResponse extends ApiItemResponse<Decision> { }

export interface ListDecisionsResponse extends ApiListResponse<Decision> { }

// ---------- Users / Roles / Tenants ----------

export interface ListUsersResponse extends ApiListResponse<User> { }

export interface ListRolesResponse extends ApiListResponse<Role> { }

export interface ListTenantsResponse extends ApiListResponse<Tenant> { }

export interface ListSpacesResponse extends ApiListResponse<Space> { }

export interface EffectivePermissionsRequest {
  userId: ID;
  tenantId: ID;
  spaceId?: ID;
}

export interface EffectivePermissionsResponse extends ApiListResponse<Permission> { }

// ---------- Audit & Policies ----------

export interface AuditFilter {
  actorId?: ID;
  tenantId?: ID;
  resourceType?: string;
  action?: string;
  from?: ISO8601;
  to?: ISO8601;
}

export interface ListAuditResponse extends ApiListResponse<AuditEntry> { }

export interface ListPoliciesResponse extends ApiListResponse<Policy> { }

export interface GetPolicyResponse extends ApiItemResponse<Policy> { }

// ---------- Collections / Vector search ----------

export interface ListCollectionsResponse extends ApiListResponse<Collection> { }

export interface VectorSearchRequest {
  collectionId: ID;
  query: VectorQuery;
}

export interface VectorSearchResponse extends ApiListResponse<VectorSearchResult> { }

// ---------- Graph ----------

export interface GraphQueryParams {
  tenantId?: ID;
  spaceId?: ID;
  nodeType?: GraphNodeType;
  from?: ISO8601;
  to?: ISO8601;
}

export interface GraphResponse {
  data: {
    nodes: GraphNode[];
    edges: GraphEdge[];
  };
  meta?: Record<string, unknown>;
}

// ---------- Observability / Analytics ----------

export interface TenantAnalyticsRow {
  tenantId: ID;
  eventCount: number;
}

export interface TenantAnalyticsResponse {
  windowHours: number;
  tenantId?: ID;
  data: TenantAnalyticsRow[];
}

