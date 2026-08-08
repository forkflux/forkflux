"""Add TargetRole.is_deleted soft-delete column and partial unique index

Revision ID: f1a2b3c4d5e6
Revises: fix_sqlite_job_status
Create Date: 2026-08-06 19:30:00.000000+00:00

This migration introduces soft-delete semantics for ``target_role``:

1. Adds a NOT NULL ``is_deleted`` boolean (default ``false``).
2. Drops the table-level ``UNIQUE`` constraint on ``role_key``.
3. Creates a partial unique index ``uq_target_role_role_key_active`` that
   enforces ``role_key`` uniqueness only among active rows
   (``WHERE is_deleted = false``).

Dropping the table constraint requires ``batch_alter_table`` on SQLite
(SQLite cannot drop an inline ``UNIQUE`` constraint without recreating the
table) and ``op.drop_constraint`` on PostgreSQL.

The ``is_deleted = false`` predicate is dialect-portable: PostgreSQL accepts
the ``false`` literal, and SQLite (>= 3.23, far older than Python's bundled
build) accepts ``false`` and stores ``Boolean`` as ``0``/``1``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "fix_sqlite_job_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Name of the partial unique index that enforces role_key uniqueness among
# non-deleted rows. Kept in sync with the Index declared on TargetRole.
_PARTIAL_UNIQUE_INDEX = "uq_target_role_role_key_active"

# Auto-generated table-level unique constraint name for role_key on
# PostgreSQL (``<table>_<column>_key``). Reflected back out for SQLite via
# MetaData to drop it during the batch recreate.
_PG_ROLE_KEY_CONSTRAINT = "target_role_role_key_key"


def upgrade() -> None:
    """Upgrade schema — soft-delete support for target_role."""
    bind = op.get_bind()

    # 1. Add the is_deleted column with a server-side default so existing
    #    rows backfill to ``false`` while the column stays NOT NULL.
    op.add_column(
        "target_role",
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # 2. Drop the table-level UNIQUE constraint on role_key (dialect-aware).
    if bind.dialect.name == "sqlite":
        # SQLite cannot drop an inline UNIQUE constraint without recreating
        # the table. Reflect the existing table, strip the role_key unique
        # constraint, and recreate. The partial unique index is added after.
        metadata = sa.MetaData()
        metadata.reflect(bind, only=["target_role"])
        target_role_table = metadata.tables["target_role"]

        target_role_table.constraints = {
            c
            for c in target_role_table.constraints
            if not (isinstance(c, sa.UniqueConstraint) and _has_column(c, "role_key"))
        }

        with op.batch_alter_table(
            "target_role",
            copy_from=target_role_table,
            recreate="always",
        ):
            # No-op Alter operations preserve the reflected structure; the
            # constraint removal above is what changes the recreated table.
            pass
    else:
        op.drop_constraint(_PG_ROLE_KEY_CONSTRAINT, "target_role", type_="unique")

    # 3. Create the partial unique index (UNIQUE role_key WHERE is_deleted = false).
    op.create_index(
        _PARTIAL_UNIQUE_INDEX,
        "target_role",
        ["role_key"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
        sqlite_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    """Downgrade schema — revert soft-delete support for target_role."""
    bind = op.get_bind()

    op.drop_index(_PARTIAL_UNIQUE_INDEX, table_name="target_role")

    if bind.dialect.name == "sqlite":
        metadata = sa.MetaData()
        metadata.reflect(bind, only=["target_role"])
        target_role_table = metadata.tables["target_role"]

        with op.batch_alter_table(
            "target_role",
            copy_from=target_role_table,
            recreate="always",
        ) as batch_op:
            batch_op.create_unique_constraint("target_role_role_key_key", ["role_key"])
    else:
        op.create_unique_constraint(_PG_ROLE_KEY_CONSTRAINT, "target_role", ["role_key"])

    op.drop_column("target_role", "is_deleted")


def _has_column(constraint: sa.UniqueConstraint, column_name: str) -> bool:
    """Return True if *constraint* contains a column named *column_name*."""
    return any(getattr(col, "name", None) == column_name for col in constraint.columns)
