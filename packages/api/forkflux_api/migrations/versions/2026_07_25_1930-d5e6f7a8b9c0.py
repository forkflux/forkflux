"""Add pending status, retry_count/max_retries columns, and job_dependency table

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-07-25 19:30:00.000000+00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Integer
from sqlalchemy.dialects import postgresql

# Dialect-aware PK type: BigInteger on PostgreSQL, Integer on SQLite
# (SQLite requires INTEGER PRIMARY KEY for autoincrement, not BIGINT)
_PK_TYPE = sa.BigInteger().with_variant(Integer, "sqlite")

# Dialect-aware JSON type: JSONB on PostgreSQL, JSON on SQLite.
# Matches the model's JSON_NULLABLE_TYPE (with none_as_null=True).
_ROUTING_RULES_TYPE = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text(), none_as_null=True), "postgresql")

# revision identifiers, used by Alembic.
revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE job_status ADD VALUE IF NOT EXISTS 'pending'")

    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.add_column(sa.Column("retry_count", sa.SmallInteger(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("max_retries", sa.SmallInteger(), nullable=False, server_default="3"))
        # published_at becomes nullable to support PENDING jobs (no publication time yet).
        batch_op.alter_column("published_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch_op.add_column(sa.Column("routing_rules", _ROUTING_RULES_TYPE, nullable=True))

    if bind.dialect.name == "postgresql":
        op.create_check_constraint(
            "chk_routing_rules_is_array_or_null",
            "handoff_job",
            "routing_rules IS NULL OR jsonb_typeof(routing_rules) = 'array'",
        )
    elif bind.dialect.name == "sqlite":
        op.create_check_constraint(
            "chk_routing_rules_is_array_or_null",
            "handoff_job",
            "routing_rules IS NULL OR (json_valid(routing_rules) AND json_type(routing_rules) = 'array')",
        )

    op.create_table(
        "job_dependency",
        sa.Column("id", _PK_TYPE, autoincrement=True, nullable=False),
        sa.Column("upstream_job_id", _PK_TYPE, nullable=False),
        sa.Column("downstream_job_id", _PK_TYPE, nullable=False),
        sa.Column(
            "dep_type",
            sa.Enum("blocks", "reopen_of", name="dependency_type", native_enum=True),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["upstream_job_id"], ["handoff_job.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["downstream_job_id"], ["handoff_job.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("upstream_job_id", "downstream_job_id", "dep_type", name="uq_job_dependency_edge"),
    )

    op.create_index("idx_job_dependency_downstream", "job_dependency", ["downstream_job_id"])
    op.create_index("idx_job_dependency_upstream", "job_dependency", ["upstream_job_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_job_dependency_upstream", table_name="job_dependency")
    op.drop_index("idx_job_dependency_downstream", table_name="job_dependency")
    op.drop_table("job_dependency")

    # Backfill published_at for any PENDING rows before restoring NOT NULL constraint.
    # PENDING jobs (created with blocked_by) have NULL published_at; set it to created_at
    # so the column can be safely restored to NOT NULL.
    op.execute("UPDATE handoff_job SET published_at = created_at WHERE published_at IS NULL")

    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.alter_column("published_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.drop_column("max_retries")
        batch_op.drop_column("retry_count")

    # PostgreSQL enum values cannot be removed without recreating the type.
    # The 'pending' value will remain in the job_status enum on PostgreSQL,
    # which is safe because no rows reference it after the columns are dropped.

    op.drop_constraint("chk_routing_rules_is_array_or_null", "handoff_job", type_="check")

    with op.batch_alter_table("handoff_job") as batch_op:
        batch_op.drop_column("routing_rules")
