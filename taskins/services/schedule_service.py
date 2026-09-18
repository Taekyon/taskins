import logging

from sqlalchemy.orm import Session

from taskins.core import scheduling
from taskins.core.config import settings
from taskins.models.execution import Execution
from taskins.models.schedule import Schedule
from taskins.models.user import User
from taskins.models.workflow import Workflow
from taskins.services import machine_service

logger = logging.getLogger(__name__)


class ScheduleValidationError(Exception):
    pass


def list_schedules(db: Session, workflow_id: int | None = None) -> list[Schedule]:
    q = db.query(Schedule)
    if workflow_id is not None:
        q = q.filter_by(workflow_id=workflow_id)
    return q.order_by(Schedule.next_run_at.is_(None), Schedule.next_run_at).all()


def get_schedule(db: Session, schedule_id: int) -> Schedule | None:
    return db.get(Schedule, schedule_id)


def create_schedule(
    db: Session,
    workflow: Workflow,
    owner: User,
    kind: str,
    run_at_local: str | None = None,
    cron_expression: str | None = None,
    machine_alias: str | None = None,
) -> Schedule:
    if workflow.archived_at is not None:
        raise ScheduleValidationError("Workflow archivé : impossible de le planifier")
    if workflow.status != "PENDING":
        raise ScheduleValidationError(
            "Seul un workflow approuvé (PENDING) peut être planifié — le soumettre d'abord"
        )

    machine_id = None
    if machine_alias:
        machine = machine_service.get_machine_by_alias(db, machine_alias)
        if machine is None:
            raise ScheduleValidationError(f"Machine cible inconnue : '{machine_alias}'")
        machine_id = machine.id

    if kind == "ONCE":
        if not run_at_local:
            raise ScheduleValidationError("Date d'exécution requise pour une planification ponctuelle")
        try:
            next_run_at = scheduling.local_input_to_sql(run_at_local)
        except ValueError as e:
            raise ScheduleValidationError(str(e))
        if next_run_at <= scheduling.now_sql():
            raise ScheduleValidationError("La date d'exécution doit être dans le futur")
        cron_expression = None

    elif kind == "CRON":
        if not cron_expression:
            raise ScheduleValidationError("Expression cron requise")
        cron_expression = cron_expression.strip()
        if not scheduling.is_valid_cron(cron_expression):
            raise ScheduleValidationError(
                f"Expression cron invalide : '{cron_expression}' "
                "(format : minute heure jour mois jour-semaine, ex. '0 2 * * *')"
            )
        next_run_at = scheduling.next_cron_occurrence(cron_expression)

    else:
        raise ScheduleValidationError(f"Type de planification inconnu : '{kind}'")

    schedule = Schedule(
        workflow_id=workflow.id,
        kind=kind,
        cron_expression=cron_expression,
        machine_id=machine_id,
        next_run_at=next_run_at,
        is_active=1,
        owner_id=owner.id,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def set_active(db: Session, schedule: Schedule, is_active: bool) -> Schedule:
    if is_active and schedule.kind == "ONCE" and schedule.last_run_at:
        raise ScheduleValidationError(
            "Planification ponctuelle déjà déclenchée : en créer une nouvelle"
        )
    schedule.is_active = int(is_active)
    if is_active and schedule.kind == "CRON":
        # Recalcul depuis maintenant : pas de rattrapage de la période inactive.
        schedule.next_run_at = scheduling.next_cron_occurrence(schedule.cron_expression)
    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule: Schedule) -> None:
    db.delete(schedule)
    db.commit()


def materialize_due_schedules(db: Session) -> int:
    """Transforme les planifications échues en lignes `executions`. Appelée à
    chaque cycle du moteur, AVANT le traitement des exécutions en attente, pour
    qu'une occurrence échue parte dans le même cycle.

    Aucun rattrapage : une occurrence détectée avec plus de
    TASKINS_SCHEDULE_GRACE_SECONDS de retard (typiquement, application arrêtée)
    est ignorée et la planification repart à l'occurrence suivante."""
    now = scheduling.now_utc()
    now_sql = scheduling.to_sql(now)
    grace = settings.schedule_grace_seconds
    created = 0

    due = (
        db.query(Schedule)
        .filter(Schedule.is_active == 1, Schedule.next_run_at.isnot(None))
        .filter(Schedule.next_run_at <= now_sql)
        .all()
    )

    for schedule in due:
        planned = scheduling.from_sql(schedule.next_run_at)
        late_seconds = (now - planned).total_seconds()
        missed = late_seconds > grace

        if missed:
            logger.warning(
                f"Planification {schedule.id} : occurrence du {schedule.next_run_at} UTC "
                f"manquée de {int(late_seconds)}s — ignorée, aucun rattrapage."
            )
        else:
            db.add(Execution(
                workflow_id=schedule.workflow_id,
                machine_id=schedule.machine_id,
                schedule_id=schedule.id,
                status="PENDING",
            ))
            schedule.last_run_at = now_sql
            created += 1

        if schedule.kind == "ONCE":
            # Une occurrence manquée n'est pas rejouée : la planification est close.
            schedule.next_run_at = None
            schedule.is_active = 0
        else:
            schedule.next_run_at = scheduling.next_cron_occurrence(
                schedule.cron_expression, after=now
            )

        db.commit()

    return created


def to_schedule_out(schedule: Schedule) -> dict:
    return {
        "id": schedule.id,
        "workflow_id": schedule.workflow_id,
        "kind": schedule.kind,
        "cron_expression": schedule.cron_expression,
        "target_machine": schedule.machine.alias if schedule.machine else None,
        "next_run_at": scheduling.sql_to_local_display(schedule.next_run_at),
        "last_run_at": scheduling.sql_to_local_display(schedule.last_run_at),
        "is_active": bool(schedule.is_active),
        "owner_id": schedule.owner_id,
    }
