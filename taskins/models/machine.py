from sqlalchemy import Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class Machine(Base):
    __tablename__ = "machines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    host: Mapped[str] = mapped_column(Text, nullable=False)
    ssh_user: Mapped[str] = mapped_column(Text, nullable=False, default="svc-taskins")
    ssh_port: Mapped[int] = mapped_column(Integer, nullable=False, default=22)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="machine")  # noqa: F821
