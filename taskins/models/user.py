from sqlalchemy import Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_admin: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))

    groups: Mapped[list["Group"]] = relationship(  # noqa: F821
        "Group", secondary="user_groups", back_populates="users"
    )
    workflows: Mapped[list["Workflow"]] = relationship(  # noqa: F821
        "Workflow", back_populates="owner"
    )
