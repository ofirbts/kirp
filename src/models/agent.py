"""
Agent, Workflow, WorkflowRun, Task, Policy, GraphNode, and GraphEdge models.

These map the core domain entities used by the Next.js frontend to
SQLAlchemy models backed by PostgreSQL. They are designed to be used as
projections of the event stream, not as sources of truth.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
from sqlalchemy.orm import relationship

from .base import Base


class Agent(Base):
    """Agent projection.

    Mirrors `Agent` in `lib/types.ts` and `src/schemas/api_models.py`:
      - id: UUID
      - name, type, status
      - ownerUserId
      - tenantId, spaceId
      - connectedWorkflowIds
      - triggers
      - config (JSON)
      - metrics stored separately or denormalised as JSON (for now we keep
        a simple JSON blob).
    """

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    owner_user_id = Column(String(255), nullable=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    connected_workflow_ids = Column(ARRAY(UUID(as_uuid=True)), server_default="{}")
    triggers = Column(ARRAY(String), server_default="{}")
    config = Column(JSON, server_default="{}")
    metrics = Column(JSON, server_default="[]")  # list[AgentMetricSnapshot]
    last_run_at = Column(String(255), nullable=True)


class Workflow(Base):
    """Workflow projection."""

    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False)
    owner_user_id = Column(String(255), nullable=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=True, index=True)
    connected_agent_ids = Column(ARRAY(UUID(as_uuid=True)), server_default="{}")
    triggers = Column(ARRAY(String), server_default="{}")
    last_run_at = Column(String(255), nullable=True)

    runs = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowRun(Base):
    """Workflow run history."""

    __tablename__ = "workflow_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    started_at = Column(String(255), nullable=False)
    finished_at = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    triggered_by = Column(String(50), nullable=False)
    trigger_ref = Column(UUID(as_uuid=True), nullable=True)
    input = Column(JSON, server_default="{}")
    output = Column(JSON, nullable=True)
    logs = Column(JSON, server_default="[]")

    workflow = relationship("Workflow", back_populates="runs")


class Task(Base):
    """Task / job execution record."""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue = Column(String(255), nullable=False, index=True)
    worker_id = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False)
    created_at = Column(String(255), nullable=False)
    started_at = Column(String(255), nullable=True)
    finished_at = Column(String(255), nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, server_default="{}")
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    logs = Column(JSON, nullable=True)


class Policy(Base):
    """Policy definition (OPA-backed)."""

    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    engine = Column(String(50), nullable=False)  # e.g. "opa"
    source = Column(Text, nullable=False)  # policy source text (e.g. Rego)
    created_at = Column(String(255), nullable=False)
    updated_at = Column(String(255), nullable=False)


class GraphNode(Base):
    """Graph node projection.

    Mirrors `GraphNode` in the TS schema.
    """

    __tablename__ = "graph_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(String(50), nullable=False)
    label = Column(String(255), nullable=False)
    tenant_id = Column(String(255), nullable=False, index=True)
    space_id = Column(String(255), nullable=True, index=True)
    # Use a non-reserved attribute name; column remains "metadata".
    meta = Column("metadata", JSON, server_default="{}")


class GraphEdge(Base):
    """Graph edge between nodes."""

    __tablename__ = "graph_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False, index=True)
    to_id = Column(UUID(as_uuid=True), ForeignKey("graph_nodes.id"), nullable=False, index=True)
    type = Column(String(100), nullable=False)
    meta = Column("metadata", JSON, server_default="{}")

