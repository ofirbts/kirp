"""Add space_memberships table for shared context / visibility

Revision ID: 004_space_memberships
Revises: 003_core_entities
Create Date: 2026-02-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON

revision = "004_space_memberships"
down_revision = "003_core_entities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "space_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("space_id", sa.String(255), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("role", sa.String(100), nullable=True),
        sa.Column("extra", JSON, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_space_memberships_tenant_id", "space_memberships", ["tenant_id"])
    op.create_index("ix_space_memberships_space_id", "space_memberships", ["space_id"])
    op.create_index("ix_space_memberships_user_id", "space_memberships", ["user_id"])
    op.create_index("ix_space_memberships_tenant_user", "space_memberships", ["tenant_id", "user_id"])
    op.create_unique_constraint(
        "uq_space_membership_tenant_space_user",
        "space_memberships",
        ["tenant_id", "space_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_space_membership_tenant_space_user", "space_memberships", type_="unique")
    op.drop_index("ix_space_memberships_tenant_user", table_name="space_memberships")
    op.drop_index("ix_space_memberships_user_id", table_name="space_memberships")
    op.drop_index("ix_space_memberships_space_id", table_name="space_memberships")
    op.drop_index("ix_space_memberships_tenant_id", table_name="space_memberships")
    op.drop_table("space_memberships")
