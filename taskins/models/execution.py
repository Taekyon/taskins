from sqlalchemy import Integer, Text, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint("status IN ('PENDING','RUNNING','DONE','FAILED')", name="ck_execution_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(Integer, ForeignKey("workflows.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="executions")  # noqa: F821
    task_results: Mapped[list["TaskResult"]] = relationship(  # noqa: F821
        "TaskResult", back_populates="execution", cascade="all, delete-orphan"
    )