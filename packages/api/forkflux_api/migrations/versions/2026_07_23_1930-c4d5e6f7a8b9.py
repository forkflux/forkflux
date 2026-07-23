"""Add unblocked status, unblock_reason and unblocked_at columns to handoff_job

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-07-23 19:30:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'unblocked'")

    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.add_column(sa.Column("unblock_reason", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("unblocked_at", sa.DateTime(timezone=True), nullable=True))

    with op.batch_alter_table("job_event") as batch_op:
        batch_op.drop_column("previous_status")


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.drop_column("unblocked_at")
        batch_op.drop_column("unblock_reason")

    # PostgreSQL enum values cannot be removed without recreating the type.
    # The 'unblocked' value will remain in the job_status enum on PostgreSQL,
    # which is safe because no rows reference it after the columns are dropped.

    with op.batch_alter_table("job_event") as batch_op:
        batch_op.add_column(
            sa.Column(
                "previous_status",
                sa.Enum(
                    "published",
                    "claimed",
                    "in_progress",
                    "blocked",
                    "unblocked",
                    "completed",
                    "failed",
                    "cancelled",
                    name="job_status",
                    native_enum=True,
                ),
                nullable=True,
            )
        )
