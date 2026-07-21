import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from taskins.core.config import settings
from taskins.core.database import SessionLocal
from taskins.core.ssh_client import SSHInfrastructureError, execute_command
from taskins.models.execution import Execution
from taskins.models.task import Task
from taskins.models.task_result import TaskResult

logger = logging.getLogger(__name__)


def _now() -> str:
    # Même format que SQLite datetime('now') : 'YYYY-MM-DD HH:MM:SS', UTC.
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def scan_and_process_pending_executions() -> None:
    """Un cycle du moteur. Fonction synchrone — voir run_engine_loop pour
    l'explication de pourquoi elle est déportée dans un thread."""
    db = SessionLocal()
    try:
        pending_ids = [e.id for e in db.query(Execution).filter_by(status="PENDING").all()]
        for execution_id in pending_ids:
            _process_execution(db, execution_id)
    finally:
        db.close()


def _process_execution(db: Session, execution_id: int) -> None:
    execution = db.get(Execution, execution_id)
    if execution is None or execution.status != "PENDING":
        return  # déjà traitée entre-temps

    execution.status = "RUNNING"
    execution.started_at = _now()
    db.commit()

    tasks = (
        db.query(Task)
        .filter_by(workflow_id=execution.workflow_id)
        .order_by(Task.order_index)
        .all()
    )

    for task in tasks:
        task_result = TaskResult(
            execution_id=execution.id,
            task_id=task.id,
            status="RUNNING",
            started_at=_now(),
        )
        db.add(task_result)
        db.commit()
        db.refresh(task_result)

        if task.condition_task_id is not None:
            ref_result = (
                db.query(TaskResult)
                .filter_by(execution_id=execution.id, task_id=task.condition_task_id)
                .first()
            )
            condition_met = (
                ref_result is not None and ref_result.return_code == task.condition_expected_code
            )
            if not condition_met:
                logger.info(
                    f"Exécution {execution.id} : condition non satisfaite sur '{task.name}', arrêt."
                )
                task_result.status = "FAILED"
                task_result.finished_at = _now()
                execution.status = "FAILED"
                execution.finished_at = _now()
                db.commit()
                return

        machine = task.machine
        try:
            result = execute_command(
                host=machine.host,
                port=machine.ssh_port,
                username=machine.ssh_user,
                key_path=settings.ssh_key_path,
                command=task.command,
            )
        except SSHInfrastructureError as e:
            logger.error(f"Exécution {execution.id}, tâche '{task.name}' : {e}")
            task_result.status = "FAILED"
            task_result.stderr = str(e)
            task_result.finished_at = _now()
            execution.status = "FAILED"
            execution.finished_at = _now()
            db.commit()
            return

        task_result.status = "DONE"
        task_result.return_code = result.return_code
        task_result.stdout = result.stdout
        task_result.stderr = result.stderr
        task_result.finished_at = _now()
        db.commit()

    execution.status = "DONE"
    execution.finished_at = _now()
    db.commit()


async def run_engine_loop() -> None:
    """Boucle asyncio de fond. scan_and_process_pending_executions() est
    entièrement synchrone (SQLAlchemy sync + paramiko, aucun des deux n'est
    async-natif) : l'exécuter en direct dans cette coroutine bloquerait tout
    le event loop — donc aussi les requêtes HTTP en cours — pendant chaque
    connexion SSH. asyncio.to_thread() la déporte dans un thread, ce qui
    garde le serveur web réactif pendant que le moteur travaille."""
    while True:
        try:
            await asyncio.to_thread(scan_and_process_pending_executions)
        except Exception as e:
            logger.error(f"Erreur dans le cycle du moteur : {e}")
        await asyncio.sleep(settings.scheduler_interval)
