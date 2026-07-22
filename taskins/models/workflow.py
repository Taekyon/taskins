from sqlalchemy import Integer, Text, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        CheckConstraint("status IN ('DRAFT','PENDING_APPROVAL','PENDING')", name="ck_workflow_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="DRAFT")
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))
    updated_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))
    # Archivage (suppression douce) : masqué des listes, historique conservé.
    archived_at: Mapped[str | None] = mapped_column(Text)

    owner: Mapped["User"] = relationship("User", back_populates="workflows")  # noqa: F821
    group: Mapped["Group"] = relationship("Group", back_populates="workflows")  # noqa: F821
    tasks: Mapped[list["Task"]] = relationship(  # noqa: F821
        "Task", back_populates="workflow", cascade="all, delete-orphan"
    )
    # cascade : la suppression définitive d'un workflow emporte ses exécutions
    # (et, via Execution.task_results, leurs résultats).
    executions: Mapped[list["Execution"]] = relationship(  # noqa: F821
        "Execution", back_populates="workflow", cascade="all, delete-orphan"
    )
    schedules: Mapped[list["Schedule"]] = relationship(  # noqa: F821
        "Schedule", back_populates="workflow", cascade="all, delete-orphan"
    )
