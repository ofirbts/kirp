"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSON

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tenants
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('extra', JSON, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Spaces
    op.create_table(
        'spaces',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.String(255), nullable=True),
        sa.Column('extra', JSON, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Events (metadata)
    op.create_table(
        'events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('space_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('source', sa.String(255), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('sensitivity', sa.String(50), nullable=False),
        sa.Column('trace_id', sa.String(255), nullable=True),
        sa.Column('extra', JSON, server_default=sa.text("'{}'")),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('embedding', ARRAY(sa.Float), nullable=True),
        sa.Column('risk_score', sa.Float, nullable=True),
        sa.Column('requires_approval', sa.Boolean, default=False),
        sa.Column('approved', sa.Boolean, nullable=True),
        sa.Column('approved_by', sa.String(255), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_events_tenant_id', 'events', ['tenant_id'])
    op.create_index('ix_events_space_id', 'events', ['space_id'])
    op.create_index('ix_events_user_id', 'events', ['user_id'])
    op.create_index('ix_events_event_type', 'events', ['event_type'])
    op.create_index('ix_events_trace_id', 'events', ['trace_id'])
    op.create_index('ix_events_timestamp', 'events', ['timestamp'])

    # Audit logs
    op.create_table(
        'audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(255), nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=True),
        sa.Column('result', sa.String(50), nullable=False),
        sa.Column('policy_id', sa.String(255), nullable=True),
        sa.Column('risk_score', sa.Float, nullable=True),
        sa.Column('details', JSON, server_default=sa.text("'{}'")),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'])

    # Schema nodes
    op.create_table(
        'schema_nodes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('space_id', sa.String(255), nullable=False),
        sa.Column('entity', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('extra', JSON, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_schema_nodes_tenant_id', 'schema_nodes', ['tenant_id'])
    op.create_index('ix_schema_nodes_space_id', 'schema_nodes', ['space_id'])
    op.create_index('ix_schema_nodes_entity', 'schema_nodes', ['entity'])

    # Users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(255), unique=True, nullable=False),
        sa.Column('email', sa.String(255), unique=True, nullable=True),
        sa.Column('tenant_id', sa.String(255), nullable=False),
        sa.Column('extra', JSON, server_default=sa.text("'{}'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])

    # Roles
    op.create_table(
        'roles',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('permissions', JSON, server_default=sa.text("'[]'")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # User-Role mapping
    op.create_table(
        'user_roles',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('role_id', UUID(as_uuid=True), sa.ForeignKey('roles.id'), primary_key=True),
    )

    # Permissions
    op.create_table(
        'permissions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')
    op.drop_table('schema_nodes')
    op.drop_table('audit_logs')
    op.drop_table('events')
    op.drop_table('spaces')
    op.drop_table('tenants')
