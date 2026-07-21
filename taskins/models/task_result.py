from sqlalchemy import Integer, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class TaskResult(Base):
    __tablename__ = "task_results"
    __table_args__ = (
        UniqueConstraint("execution_id", "task_id", name="uq_taskresult_execution_task"),
        CheckConstraint("status IN ('PENDING','RUNNING','DONE','FAILED')", name="ck_taskresult_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    execution_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(Integer, ForeignKey("tasks.id"), nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="PENDING")
    return_code: Mapped[int | None] = mapped_column(Integer)
    stdout: Mapped[str | None] = mapped_column(Text)
    stderr: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[str | None] = mapped_column(Text)
    finished_at: Mapped[str | None] = mapped_column(Text)

    execution: Mapped["Execution"] = relationship("Execution", back_populates="task_results")  # noqa: F821
    task: Mapped["Task"] = relationship("Task", back_populates="results")  # noqa: F821