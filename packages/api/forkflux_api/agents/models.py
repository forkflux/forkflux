from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from forkflux_api.database import Base, UTCDateTime

PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class TargetRole(Base):
    __tablename__ = "target_role"

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    role_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    role_label: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class AgentIdentity(Base):
    __tablename__ = "agent_identity"

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    agent_label: Mapped[str] = mapped_column(Text, nullable=False)
    tool_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    role_assignments: Mapped[list["AgentIdentityRole"]] = relationship(
        back_populates="agent_identity",
        cascade="all, delete-orphan",
        lazy="raise",
    )

    @property
    def roles(self) -> list["TargetRole"]:
        return [assignment.target_role for assignment in self.role_assignments]


class AgentIdentityRole(Base):
    __tablename__ = "agent_identity_role"
    __table_args__ = (UniqueConstraint("agent_identity_id", "target_role_id", name="uq_agent_identity_role_pair"),)

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    agent_identity_id: Mapped[int] = mapped_column(ForeignKey("agent_identity.id", ondelete="CASCADE"), nullable=False)
    target_role_id: Mapped[int] = mapped_column(ForeignKey("target_role.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    agent_identity: Mapped["AgentIdentity"] = relationship(back_populates="role_assignments")
    target_role: Mapped["TargetRole"] = relationship()


class AgentApiToken(Base):
    __tablename__ = "agent_api_token"

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_identity.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
