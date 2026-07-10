"""

Revision ID: 9b2f1a4c6d7e
Revises: ef0279dd14c3
Create Date: 2026-07-09 19:30:00.000000+00:00

"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b2f1a4c6d7e"
down_revision: Union[str, Sequence[str], None] = "ef0279dd14c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _id_type() -> Any:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    """Upgrade schema."""
    id_type = _id_type()

    op.create_table(
        "agent_identity_role",
        sa.Column("id", id_type, autoincrement=True, nullable=False),
        sa.Column("agent_identity_id", id_type, nullable=False),
        sa.Column("target_role_id", id_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["agent_identity_id"], ["agent_identity.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_role_id"], ["target_role.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_identity_id", "target_role_id", name="uq_agent_identity_role_pair"),
    )
    op.create_index(
        "idx_agent_identity_role_agent_identity",
        "agent_identity_role",
        ["agent_identity_id", "target_role_id"],
        unique=False,
    )

    op.execute(
        sa.text(
            """
            INSERT INTO agent_identity_role (agent_identity_id, target_role_id, created_at)
            SELECT id, role_id, created_at
            FROM agent_identity
            """
        )
    )

    with op.batch_alter_table("agent_identity") as batch_op:
        batch_op.drop_column("role_id")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    with op.batch_alter_table("agent_identity") as batch_op:
        batch_op.add_column(sa.Column("role_id", _id_type(), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
                UPDATE agent_identity ai
                SET role_id = src.target_role_id
                FROM (
                    SELECT agent_identity_id, MIN(target_role_id) AS target_role_id
                    FROM agent_identity_role
                    GROUP BY agent_identity_id
                ) AS src
                WHERE ai.id = src.agent_identity_id
                """
            )
        )
    else:
        op.execute(
            sa.text(
                """
                UPDATE agent_identity
                SET role_id = (
                    SELECT MIN(air.target_role_id)
                    FROM agent_identity_role AS air
                    WHERE air.agent_identity_id = agent_identity.id
                )
                """
            )
        )

    null_count = bind.execute(sa.text("SELECT COUNT(*) FROM agent_identity WHERE role_id IS NULL")).scalar()

    if null_count:
        raise RuntimeError(
            f"Cannot enforce non-null role_id: {null_count} agent_identity row(s) "
            "still have NULL role_id after backfill from agent_identity_role. "
            "Assign a target_role to these agents before downgrading."
        )

    with op.batch_alter_table("agent_identity") as batch_op:
        batch_op.alter_column("role_id", nullable=False)
        batch_op.create_foreign_key("fk_agent_identity_role_id_target_role", "target_role", ["role_id"], ["id"])

    op.drop_index("idx_agent_identity_role_agent_identity", table_name="agent_identity_role")
    op.drop_table("agent_identity_role")
