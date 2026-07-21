"""Create profile table

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-07-20 19:30:00.000000+00:00

"""

from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _id_type() -> Any:
    return sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    """Upgrade schema."""
    id_type = _id_type()

    op.create_table(
        "profile",
        sa.Column("id", id_type, autoincrement=True, nullable=False),
        sa.Column("is_onboarded", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("profile")
