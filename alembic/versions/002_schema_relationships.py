"""Add schema relationships and task fields

Revision ID: 002_schema_relationships
Revises: 001_initial
Create Date: 2026-01-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers
revision = '002_schema_relationships'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to schema_nodes
    op.add_column('schema_nodes', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('schema_nodes', sa.Column('parent_id', UUID(as_uuid=True), nullable=True))
    op.add_column('schema_nodes', sa.Column('status', sa.String(50), nullable=True))
    op.add_column('schema_nodes', sa.Column('priority', sa.String(50), nullable=True))
    op.add_column('schema_nodes', sa.Column('due_date', sa.DateTime(timezone=True), nullable=True))
    op.add_column('schema_nodes', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add foreign key for parent relationship
    op.create_foreign_key(
        'fk_schema_nodes_parent_id',
        'schema_nodes', 'schema_nodes',
        ['parent_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add indexes
    op.create_index('ix_schema_nodes_parent_id', 'schema_nodes', ['parent_id'])
    op.create_index('ix_schema_nodes_status', 'schema_nodes', ['status'])
    op.create_index('ix_schema_nodes_priority', 'schema_nodes', ['priority'])
    op.create_index('ix_schema_nodes_due_date', 'schema_nodes', ['due_date'])


def downgrade() -> None:
    op.drop_index('ix_schema_nodes_due_date', table_name='schema_nodes')
    op.drop_index('ix_schema_nodes_priority', table_name='schema_nodes')
    op.drop_index('ix_schema_nodes_status', table_name='schema_nodes')
    op.drop_index('ix_schema_nodes_parent_id', table_name='schema_nodes')
    op.drop_constraint('fk_schema_nodes_parent_id', 'schema_nodes', type_='foreignkey')
    op.drop_column('schema_nodes', 'deleted_at')
    op.drop_column('schema_nodes', 'due_date')
    op.drop_column('schema_nodes', 'priority')
    op.drop_column('schema_nodes', 'status')
    op.drop_column('schema_nodes', 'parent_id')
    op.drop_column('schema_nodes', 'description')
