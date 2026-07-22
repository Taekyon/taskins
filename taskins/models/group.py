from sqlalchemy import Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", secondary="user_groups", back_populates="groups"
    )
    workflows: Mapped[list["Workflow"]] = relationship(  # noqa: F821
        "Workflow", back_populates="group"
    )
