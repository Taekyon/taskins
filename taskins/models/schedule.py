from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taskins.core.database import Base


class Schedule(Base):
    """Planification d'un workflow. Une seule table couvre les deux besoins :
    exécution différée (kind='ONCE') et récurrence (kind='CRON').

    La planification ne fait que **matérialiser des lignes `executions`** ; le
    traitement reste celui du moteur existant, inchangé."""

    __tablename__ = "schedules"
    __table_args__ = (
        CheckConstraint("kind IN ('ONCE','CRON')", name="ck_schedule_kind"),
        CheckConstraint(
            "(kind = 'ONCE' AND cron_expression IS NULL) OR "
            "(kind = 'CRON' AND cron_expression IS NOT NULL)",
            name="ck_schedule_kind_fields",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    cron_expression: Mapped[str | None] = mapped_column(Text)
    # Machine de retargeting héritée par les exécutions produites. NULL = défauts.
    machine_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("machines.id"))
    # Prochaine occurrence, en UTC. NULL = plus rien à déclencher.
    next_run_at: Mapped[str | None] = mapped_column(Text)
    last_run_at: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(Text, nullable=False, server_default=func.datetime("now"))

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="schedules")  # noqa: F821
    machine: Mapped["Machine | None"] = relationship("Machine")  # noqa: F821
    owner: Mapped["User"] = relationship("User")  # noqa: F821
