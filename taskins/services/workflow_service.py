from datetime import datetime, timezone

from sqlalchemy.orm import Session

from taskins.models.execution import Execution
from taskins.models.group import Group
from taskins.models.task import Task
from taskins.models.user import User
from taskins.models.workflow import Workflow
from taskins.schemas.workflow import WorkflowCreate
from taskins.services import machine_service


class WorkflowValidationError(Exception):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _default_group(db: Session) -> Group:
    # V1 : visibilité non appliquée, groupe unique "all" (06-controle-acces.md).
    group = db.query(Group).filter_by(name="all").first()
    if group is None:
        raise RuntimeError("Groupe 'all' introuvable — seed non exécuté")
    return group


def create_workflow(db: Session, data: WorkflowCreate, owner: User) -> Workflow:
    group = _default_group(db)

    # Résoudre tous les alias de machine avant toute écriture.
    machines_by_alias = {}
    for task_in in data.tasks:
        if task_in.target not in machines_by_alias:
            machine = machine_service.get_machine_by_alias(db, task_in.target)
            if machine is None:
                raise WorkflowValidationError(f"Machine cible inconnue : '{task_in.target}'")
            machines_by_alias[task_in.target] = machine

    workflow = Workflow(
        name=data.name,
        description=data.description,
        owner_id=owner.id,
        group_id=group.id,
        status="DRAFT",
    )
    db.add(workflow)
    db.flush()  # obtenir workflow.id sans committer

    tasks_by_name: dict[str, Task] = {}
    for index, task_in in enumerate(data.tasks, start=1):
        task = Task(
            workflow_id=workflow.id,
            name=task_in.name,
            command=task_in.command,
            machine_id=machines_by_alias[task_in.target].id,
            order_index=index,
            timeout_seconds=task_in.timeout_seconds,
        )
        db.add(task)
        db.flush()
        tasks_by_name[task_in.name] = task

    # Deuxième passe : les tâches référencées par une condition existent déjà en base.
    for task_in in data.tasks:
        if task_in.condition is not None:
            task = tasks_by_name[task_in.name]
            task.condition_task_id = tasks_by_name[task_in.condition.task].id
            task.condition_expected_code = task_in.condition.return_code

    db.commit()
    db.refresh(workflow)
    return workflow


def list_workflows(db: Session, include_archived: bool = False) -> list[Workflow]:
    q = db.query(Workflow)
    if not include_archived:
        q = q.filter(Workflow.archived_at.is_(None))
    return q.order_by(Workflow.created_at.desc()).all()


def archive_workflow(db: Session, workflow: Workflow) -> Workflow:
    """Suppression douce : le workflow disparaît des listes mais son historique
    d'exécutions reste consultable. Réversible."""
    if workflow.archived_at is not None:
        raise WorkflowValidationError("Workflow déjà archivé")
    workflow.archived_at = _now()
    db.commit()
    db.refresh(workflow)
    return workflow


def unarchive_workflow(db: Session, workflow: Workflow) -> Workflow:
    if workflow.archived_at is None:
        raise WorkflowValidationError("Workflow non archivé")
    workflow.archived_at = None
    db.commit()
    db.refresh(workflow)
    return workflow


def delete_workflow(db: Session, workflow: Workflow) -> None:
    """Suppression définitive : emporte les tâches, les exécutions et tout
    l'historique des résultats. Irréversible."""
    db.delete(workflow)
    db.commit()


def get_workflow(db: Session, workflow_id: int) -> Workflow | None:
    return db.get(Workflow, workflow_id)


def submit_workflow(db: Session, workflow: Workflow) -> Workflow:
    if workflow.status != "DRAFT":
        raise WorkflowValidationError("Seul un workflow en DRAFT peut être soumis")
    # Transition automatique en V1 (05-moteur-ordonnancement.md) : pas d'approbation admin réelle.
    workflow.status = "PENDING"
    db.commit()
    db.refresh(workflow)
    return workflow


def execute_workflow(
    db: Session, workflow: Workflow, machine_alias: str | None = None
) -> Execution:
    """Crée une exécution en attente. `machine_alias` permet de rediriger toutes
    les tâches vers une autre machine sans toucher à la définition du workflow
    (retargeting, option B) — la définition reste immuable."""
    if workflow.archived_at is not None:
        raise WorkflowValidationError("Workflow archivé : le désarchiver avant de l'exécuter")
    if workflow.status != "PENDING":
        raise WorkflowValidationError("Seul un workflow approuvé (PENDING) peut être exécuté")

    machine_id = None
    if machine_alias:
        machine = machine_service.get_machine_by_alias(db, machine_alias)
        if machine is None:
            raise WorkflowValidationError(f"Machine cible inconnue : '{machine_alias}'")
        machine_id = machine.id

    execution = Execution(workflow_id=workflow.id, status="PENDING", machine_id=machine_id)
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def to_execution_out(execution: Execution) -> dict:
    return {
        "id": execution.id,
        "status": execution.status,
        "started_at": execution.started_at,
        "finished_at": execution.finished_at,
        "target_machine": execution.machine.alias if execution.machine else None,
    }


def to_task_result_out(result) -> dict:
    return {
        "id": result.id,
        "task_name": result.task.name,
        "status": result.status,
        "return_code": result.return_code,
        "command": result.command,
        "machine_alias": result.machine_alias,
        "machine_host": result.machine_host,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "started_at": result.started_at,
        "finished_at": result.finished_at,
    }


def to_workflow_out(workflow: Workflow) -> dict:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "status": workflow.status,
        "owner_id": workflow.owner_id,
        "group_id": workflow.group_id,
        "created_at": workflow.created_at,
        "archived_at": workflow.archived_at,
    }


def to_workflow_detail(workflow: Workflow) -> dict:
    tasks_by_id = {t.id: t for t in workflow.tasks}
    tasks_out = []
    for t in sorted(workflow.tasks, key=lambda x: x.order_index):
        condition = None
        if t.condition_task_id is not None:
            ref_task = tasks_by_id[t.condition_task_id]
            condition = {"task": ref_task.name, "return_code": t.condition_expected_code}
        tasks_out.append({
            "id": t.id,
            "name": t.name,
            "command": t.command,
            "target": t.machine.alias,
            "order_index": t.order_index,
            "condition": condition,
            "timeout_seconds": t.timeout_seconds,
        })
    return {**to_workflow_out(workflow), "tasks": tasks_out}
