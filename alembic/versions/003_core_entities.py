"""Add core projection entities

Revision ID: 003_core_entities
Revises: 002_schema_relationships
Create Date: 2026-01-28

This migration creates the relational projection tables for the core domain
entities used by the Intelligence OS frontend: agents, workflows,
workflow_runs, tasks, policies, graph_nodes, and graph_edges.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY


# revision identifiers, used by Alembic.
revision = "003_core_entities"
down_revision = "002_schema_relationships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("owner_user_id", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("space_id", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("connected_workflow_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("triggers", ARRAY(sa.String()), server_default="{}"),
        sa.Column("config", JSON, server_default=sa.text("'{}'")),
        sa.Column("metrics", JSON, server_default=sa.text("'[]'")),
        sa.Column("last_run_at", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_agents_tenant_id", "agents", ["tenant_id"])
    op.create_index("ix_agents_space_id", "agents", ["space_id"])

    # Workflows
    op.create_table(
        "workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("owner_user_id", sa.String(length=255), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("space_id", sa.String(length=255), nullable=True),
        sa.Column("connected_agent_ids", ARRAY(UUID(as_uuid=True)), server_default="{}"),
        sa.Column("triggers", ARRAY(sa.String()), server_default="{}"),
        sa.Column("last_run_at", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_workflows_tenant_id", "workflows", ["tenant_id"])
    op.create_index("ix_workflows_space_id", "workflows", ["space_id"])

    # Workflow runs
    op.create_table(
        "workflow_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("started_at", sa.String(length=255), nullable=False),
        sa.Column("finished_at", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("triggered_by", sa.String(length=50), nullable=False),
        sa.Column("trigger_ref", UUID(as_uuid=True), nullable=True),
        sa.Column("input", JSON, server_default=sa.text("'{}'")),
        sa.Column("output", JSON, nullable=True),
        sa.Column("logs", JSON, server_default=sa.text("'[]'")),
    )
    op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"])

    # Tasks
    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("queue", sa.String(length=255), nullable=False),
        sa.Column("worker_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.String(length=255), nullable=True),
        sa.Column("finished_at", sa.String(length=255), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payload", JSON, server_default=sa.text("'{}'")),
        sa.Column("result", JSON, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("logs", JSON, nullable=True),
    )
    op.create_index("ix_tasks_queue", "tasks", ["queue"])
    op.create_index("ix_tasks_status", "tasks", ["status"])

    # Policies
    op.create_table(
        "policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("engine", sa.String(length=50), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.String(length=255), nullable=False),
    )
    op.create_index("ix_policies_name", "policies", ["name"], unique=True)

    # Graph nodes
    op.create_table(
        "graph_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("space_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", JSON, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_graph_nodes_tenant_id", "graph_nodes", ["tenant_id"])
    op.create_index("ix_graph_nodes_space_id", "graph_nodes", ["space_id"])

    # Graph edges
    op.create_table(
        "graph_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("from_id", UUID(as_uuid=True), sa.ForeignKey("graph_nodes.id"), nullable=False),
        sa.Column("to_id", UUID(as_uuid=True), sa.ForeignKey("graph_nodes.id"), nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("metadata", JSON, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_graph_edges_from_id", "graph_edges", ["from_id"])
    op.create_index("ix_graph_edges_to_id", "graph_edges", ["to_id"])


def downgrade() -> None:
    op.drop_index("ix_graph_edges_to_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_from_id", table_name="graph_edges")
    op.drop_table("graph_edges")

    op.drop_index("ix_graph_nodes_space_id", table_name="graph_nodes")
    op.drop_index("ix_graph_nodes_tenant_id", table_name="graph_nodes")
    op.drop_table("graph_nodes")

    op.drop_index("ix_policies_name", table_name="policies")
    op.drop_table("policies")

    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_queue", table_name="tasks")
    op.drop_table("tasks")

    op.drop_index("ix_workflow_runs_workflow_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

    op.drop_index("ix_workflows_space_id", table_name="workflows")
    op.drop_index("ix_workflows_tenant_id", table_name="workflows")
    call: { "command": "echo 'patching api routers to use schemas'", "working_directory": "/home/ofir/projects/kirp", "block_until_ms": 1000, "description": "noop marker command", "required_permissions": []}
    op.drop_table("workflows")

    op.drop_index("ix_agents_space_id", table_name="agents")
    op.drop_index("ix_agents_tenant_id", table_name="agents")
    op.drop_table("agents")

