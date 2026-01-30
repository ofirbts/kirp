"""
Pydantic models that mirror the TypeScript interfaces in `lib/types.ts`.

These models are used by the /api/* routers to ensure the JSON responses
match the frontend expectations exactly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------- API schema version ----------

API_SCHEMA_VERSION = "1.0.0"


# ---------- Shared scalar aliases ----------

ID = str
ISO8601 = str


# ---------- Metrics ----------


class AgentMetricSnapshot(BaseModel):
    timestamp: ISO8601
    successRate: float
    avgLatencyMs: float
    errorRate: float
    invocations: int


# ---------- Tenancy ----------


class Tenant(BaseModel):
    id: ID
    name: str
    slug: str
    createdAt: ISO8601
    updatedAt: ISO8601


class Space(BaseModel):
    id: ID
    tenantId: ID
    name: str
    slug: str
    createdAt: ISO8601
    updatedAt: ISO8601


# ---------- Identity & Access ----------


class Permission(BaseModel):
    resource: str
    action: str
    scope: str  # "tenant" | "space" | "global"


class Role(BaseModel):
    id: ID
    name: str
    description: Optional[str] = None
    inheritedRoleIds: Optional[List[ID]] = None
    permissions: List[Permission]


class User(BaseModel):
    id: ID
    email: str
    name: str
    status: str  # "active" | "disabled" | "invited"
    roles: List[ID]
    tenants: List[ID]
    spaces: List[ID]
    createdAt: ISO8601
    lastLoginAt: Optional[ISO8601] = None


# ---------- Governance & Audit ----------


class Policy(BaseModel):
    id: ID
    name: str
    description: Optional[str] = None
    engine: str  # "opa"
    source: str
    createdAt: ISO8601
    updatedAt: ISO8601


class AuditEntry(BaseModel):
    id: ID
    timestamp: ISO8601
    actorType: str  # "user" | "agent" | "system"
    actorId: ID
    tenantId: ID
    spaceId: Optional[ID] = None
    action: str
    resourceType: str
    resourceId: Optional[ID] = None
    metadata: Dict[str, Any]
    result: str  # "success" | "failure"


# ---------- Agents ----------


class Agent(BaseModel):
    id: ID
    name: str
    type: str
    status: str
    ownerUserId: Optional[ID] = None
    description: Optional[str] = None
    lastRunAt: Optional[ISO8601] = None
    tenantId: ID
    spaceId: Optional[ID] = None
    connectedWorkflowIds: List[ID]
    triggers: List[str]
    config: Dict[str, Any]
    metrics: List[AgentMetricSnapshot]


# ---------- Events ----------


class Event(BaseModel):
    id: ID
    timestamp: ISO8601
    topic: str
    key: Optional[str] = None
    tenantId: ID
    spaceId: Optional[ID] = None
    agentId: Optional[ID] = None
    severity: str
    payloadPreview: str
    payload: Any
    source: str
    status: Optional[str] = None


# ---------- Decisions ----------


class DecisionInputRef(BaseModel):
    type: str
    id: ID


class DecisionTraceStep(BaseModel):
    id: ID
    timestamp: ISO8601
    agentId: Optional[ID] = None
    description: str
    inputSummary: str
    outputSummary: str
    raw: Optional[Any] = None


class Decision(BaseModel):
    id: ID
    createdAt: ISO8601
    tenantId: ID
    spaceId: Optional[ID] = None
    agentId: ID
    workflowId: Optional[ID] = None
    inputs: List[DecisionInputRef]
    trace: List[DecisionTraceStep]
    output: Any
    confidence: float
    status: str
    errorMessage: Optional[str] = None


# ---------- Workflows ----------


class Workflow(BaseModel):
    id: ID
    name: str
    description: Optional[str] = None
    status: str
    ownerUserId: Optional[ID] = None
    connectedAgentIds: List[ID]
    triggers: List[str]
    lastRunAt: Optional[ISO8601] = None


class WorkflowRun(BaseModel):
    id: ID
    workflowId: ID
    startedAt: ISO8601
    finishedAt: Optional[ISO8601] = None
    status: str
    triggeredBy: str
    triggerRef: Optional[ID] = None
    input: Any
    output: Optional[Any] = None
    logs: List[str]


# ---------- Tasks ----------


class Task(BaseModel):
    id: ID
    queue: str
    workerId: Optional[str] = None
    status: str
    createdAt: ISO8601
    startedAt: Optional[ISO8601] = None
    finishedAt: Optional[ISO8601] = None
    attempts: int
    maxAttempts: int
    payload: Any
    result: Optional[Any] = None
    error: Optional[str] = None
    logs: Optional[List[str]] = None


# ---------- Collections / Documents / Vectors ----------


class Collection(BaseModel):
    id: ID
    name: str
    description: Optional[str] = None
    vectorSize: int
    metadataSchema: Optional[Dict[str, str]] = None


class VectorSearchResult(BaseModel):
    documentId: ID
    score: float
    metadata: Dict[str, Any]


# ---------- Knowledge Graph ----------


class GraphNode(BaseModel):
    id: ID
    type: str
    label: str
    tenantId: ID
    spaceId: Optional[ID] = None
    metadata: Dict[str, Any]


class GraphEdge(BaseModel):
    id: ID
    fromId: ID
    toId: ID
    type: str
    metadata: Dict[str, Any]


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class GraphResponse(BaseModel):
    data: GraphData
    meta: Optional[Dict[str, Any]] = None


# ---------- API response wrappers ----------


class ApiListResponse(BaseModel):
    data: List[Any]
    meta: Optional[Dict[str, Any]] = None


class ApiItemResponse(BaseModel):
    data: Any
    meta: Optional[Dict[str, Any]] = None


class RunAgentResponseData(BaseModel):
    decisionId: ID
    status: str


class RunAgentResponse(ApiItemResponse):
    data: RunAgentResponseData


class AgentsListResponse(ApiListResponse):
    data: List[Agent]


class AgentItemResponse(ApiItemResponse):
    data: Agent


class DecisionsListResponse(ApiListResponse):
    data: List[Decision]


class DecisionItemResponse(ApiItemResponse):
    data: Decision


class EventsListResponse(ApiListResponse):
    data: List[Event]


class WorkflowsListResponse(ApiListResponse):
    data: List[Workflow]


class WorkflowItemResponse(ApiItemResponse):
    data: Workflow


class WorkflowRunsListResponse(ApiListResponse):
    data: List[WorkflowRun]


class TasksListResponse(ApiListResponse):
    data: List[Task]


class TaskItemResponse(ApiItemResponse):
    data: Task


class UsersListResponse(ApiListResponse):
    data: List[User]


class RolesListResponse(ApiListResponse):
    data: List[Role]


class TenantsListResponse(ApiListResponse):
    data: List[Tenant]


class SpacesListResponse(ApiListResponse):
    data: List[Space]


class AuditListResponse(ApiListResponse):
    data: List[AuditEntry]


class PoliciesListResponse(ApiListResponse):
    data: List[Policy]


class PolicyItemResponse(ApiItemResponse):
    data: Policy


class CollectionsListResponse(ApiListResponse):
    data: List[Collection]


class VectorSearchResponse(ApiListResponse):
    data: List[VectorSearchResult]


class EffectivePermissionsResponse(ApiListResponse):
    data: List[Permission]

