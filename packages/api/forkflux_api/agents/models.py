from datetime import datetime

from forkflux_api.database import Base, UTCDateTime
from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

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
    role_id: Mapped[int] = mapped_column(ForeignKey("target_role.id"), nullable=False)
    tool_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class AgentApiToken(Base):
    __tablename__ = "agent_api_token"

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    agent_id: Mapped[int] = mapped_column(ForeignKey("agent_identity.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
