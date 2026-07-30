"""Drop claimed_at column and remove claimed from job_status enum

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-07-29 19:30:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# The desired job_status enum values after removing 'claimed'.
# Must match the application-level JobStatusEnum in jobs/constants.py.
_JOB_STATUS_VALUES = [
    "PENDING",
    "PUBLISHED",
    "IN_PROGRESS",
    "BLOCKED",
    "UNBLOCKED",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]

# Columns that reference the job_status enum type on PostgreSQL.
_AFFECTED_COLUMNS = [
    TableReference(table_name="handoff_job", column_name="status", table_schema="public"),
    TableReference(table_name="job_event", column_name="current_status", table_schema="public"),
]


def upgrade() -> None:
    """Upgrade schema — drop claimed_at column and remove 'claimed' from enum.

    PostgreSQL enum values cannot be removed with ALTER TYPE; we use
    alembic-postgresql-enum's sync_enum_values() which handles the
    type recreation safely.  SQLite uses CHECK constraints rather than
    native enums, so the table recreation in batch mode will exclude
    'claimed' naturally when the column is dropped.
    """
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    # 3. Remove 'claimed' from the PostgreSQL enum.
    if is_postgresql:
        op.sync_enum_values(  # type: ignore[attr-defined]
            enum_schema="public",
            enum_name="job_status",
            new_values=_JOB_STATUS_VALUES,
            affected_columns=_AFFECTED_COLUMNS,
            enum_values_to_rename=[],
        )

    # 4. Drop the claimed_at column.
    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.drop_column("claimed_at")


def downgrade() -> None:
    """Downgrade schema — restore claimed_at column and 'claimed' enum value."""
    bind = op.get_bind()
    is_postgresql = bind.dialect.name == "postgresql"

    # 1. Restore claimed_at column.
    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.add_column(sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Add 'claimed' back to the PostgreSQL enum.
    if is_postgresql:
        op.sync_enum_values(  # type: ignore[attr-defined]
            enum_schema="public",
            enum_name="job_status",
            new_values=["CLAIMED"] + _JOB_STATUS_VALUES,
            affected_columns=_AFFECTED_COLUMNS,
            enum_values_to_rename=[],
        )
