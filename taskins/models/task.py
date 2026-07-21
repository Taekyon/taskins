from sqlalchemy import Integer, Text, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("workflow_id", "name", name="uq_task_workflow_name"),
        UniqueConstraint("workflow_id", "order_index", name="uq_task_workflow_order"),
        CheckConstraint(
            "(condition_task_id IS NULL AND condition_expected_code IS NULL) OR "
            "(condition_task_id IS NOT NULL AND condition_expected_code IS NOT NULL)",
            name="ck_task_condition_pair",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    machine_id: Mapped[int] = mapped_column(Integer, ForeignKey("machines.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    condition_task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tasks.id"))
    condition_expected_code: Mapped[int | None] = mapped_column(Integer)
    # NULL = utiliser TASKINS_DEFAULT_TASK_TIMEOUT
    timeout_seconds: Mapped[int | None] = mapped_column(Integer)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="tasks")  # noqa: F821
    machine: Mapped["Machine"] = relationship("Machine", back_populates="tasks")  # noqa: F821
    results: Mapped[list["TaskResult"]] = relationship(  # noqa: F821
        "TaskResult", back_populates="task", cascade="all, delete-orphan"
    )
