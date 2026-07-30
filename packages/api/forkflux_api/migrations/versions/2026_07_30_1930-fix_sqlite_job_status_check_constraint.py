"""Fix SQLite CHECK constraint on job_status to include BLOCKED, UNBLOCKED, PENDING

Revision ID: fix_sqlite_job_status
Revises: e6f7a8b9c0d1
Create Date: 2026-07-30 19:30:00.000000+00:00

The initial migration (ef0279dd14c3) created the handoff_job table with a
CHECK constraint on the ``status`` column that only allowed these 6 values::

    PUBLISHED, CLAIMED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED

Later migrations added BLOCKED, UNBLOCKED, and PENDING but only updated the
PostgreSQL native enum.  The SQLite CHECK constraint was never patched, so
any UPDATE or INSERT with those values fails with::

    sqlite3.IntegrityError: CHECK constraint failed: job_status

This migration reflects the existing tables to find the auto-generated
constraint names, then uses ``batch_alter_table(recreate='always')`` to
drop the old CHECK constraints and create new ones with all 8 current values.
PostgreSQL is a no-op — its native enum was already patched.
"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import MetaData

# Current job_status values matching the application's JobStatusEnum.
_CURRENT_STATUS_VALUES = [
    "PENDING",
    "PUBLISHED",
    "IN_PROGRESS",
    "BLOCKED",
    "UNBLOCKED",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
]

# revision identifiers, used by Alembic.
revision: str = "fix_sqlite_job_status"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _status_check_sql(column: str) -> str:
    """Return a CHECK constraint SQL expression for *column*."""
    values = ", ".join(f"'{v}'" for v in _CURRENT_STATUS_VALUES)
    return f"{column} IN ({values})"


def upgrade() -> None:
    """Upgrade schema — rebuild the SQLite CHECK constraint on job_status columns."""
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return

    metadata = MetaData()
    metadata.reflect(bind, only=["handoff_job", "job_event"])

    handoff_table = metadata.tables["handoff_job"]

    handoff_table.constraints = {c for c in handoff_table.constraints if getattr(c, "name", None) != "job_status"}

    with op.batch_alter_table("handoff_job", copy_from=handoff_table, recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "ck_handoff_job_status",
            _status_check_sql("status"),
        )

    # --- job_event ---
    job_event_table = metadata.tables["job_event"]

    job_event_table.constraints = {
        c for c in job_event_table.constraints if getattr(c, "name", None) not in ("job_status", "job_event_status")
    }

    with op.batch_alter_table("job_event", copy_from=job_event_table, recreate="always") as batch_op:
        batch_op.create_check_constraint(
            "ck_job_event_current_status",
            _status_check_sql("current_status"),
        )


def downgrade() -> None:
    """Downgrade schema — no-op.

    Reverting the CHECK constraint to exclude BLOCKED/UNBLOCKED/PENDING
    would be destructive if any rows already use those statuses.  The
    broader set of values is a superset of the original and is safe to keep.
    """
    pass
