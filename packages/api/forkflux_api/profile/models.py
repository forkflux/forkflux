from sqlalchemy import BigInteger, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from forkflux_api.database import Base

PK_TYPE = BigInteger().with_variant(Integer, "sqlite")


class Profile(Base):
    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(PK_TYPE, primary_key=True, autoincrement=True)
    is_onboarded: Mapped[bool] = mapped_column(Boolean, nullable=False)
