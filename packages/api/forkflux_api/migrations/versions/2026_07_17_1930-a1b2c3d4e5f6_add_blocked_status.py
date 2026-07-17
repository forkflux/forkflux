"""Add blocked status, blocked_reason and blocked_at columns to handoff_job

Revision ID: a1b2c3d4e5f6
Revises: 9b2f1a4c6d7e
Create Date: 2026-07-17 19:30:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9b2f1a4c6d7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'blocked'")

    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.add_column(sa.Column("blocked_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("blocked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.drop_column("blocked_at")
        batch_op.drop_column("blocked_reason")

    # PostgreSQL enum values cannot be removed without recreating the type.
    # The 'blocked' value will remain in the job_status enum on PostgreSQL,
    # which is safe because no rows reference it after the columns are dropped.
