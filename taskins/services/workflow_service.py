from __future__ import annotations

from sqlalchemy.orm import Session

from taskins.models.workflow import Workflow
from taskins.models.task import Task
from taskins.models.machine import Machine
from taskins.models.group import Group
from taskins.schemas.workflow import WorkflowCreate


class WorkflowValidationError(Exception):
    """Structure JSON valide (Pydantic) mais violant une règle métier :
    nom de tâche dupliqué, cible inconnue, condition mal référencée."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def _validate_business_rules(data: WorkflowCreate) -> None:
    errors: list[str] = []
    seen_names: set[str] = set()  # noms des tâches STRICTEMENT antérieures

    for i, task in enumerate(data.tasks):
        prefix = f"Tâche #{i + 1} ('{task.name}')"

        if task.name in seen_names:
            errors.append(f"{prefix} : nom de tâche dupliqué.")

        if task.condition is not None and task.condition.task not in seen_names:
            errors.append(
                f"{prefix} : condition référence '{task.condition.task}', "
                f"absente ou non antérieure dans le workflow."
            )

        seen_names.add(task.name)

    if errors:
        raise WorkflowValidationError(errors)


def create_workflow(db: Session, owner_id: int, data: WorkflowCreate) -> Workflow:
    _validate_business_rules(data)

    aliases = {t.target for t in data.tasks}
    machines_by_alias = {
        m.alias: m for m in db.query(Machine).filter(Machine.alias.in_(aliases)).all()
    }
    unknown = [t.name for t in data.tasks if t.target not in machines_by_alias]
    if unknown:
        raise WorkflowValidationError(
            [f"Tâche '{t.name}' : machine cible '{t.target}' inconnue."
             for t in data.tasks if t.target not in machines_by_alias]
        )

    group = db.query(Group).filter(Group.name == "all").first()
    if group is None:
        # Ne devrait jamais arriver : groupe injecté par _seed() au démarrage (core/database.py)
        raise RuntimeError("Groupe 'all' introuvable en base.")

    workflow = Workflow(
        name=data.name,
        description=data.description,
        owner_id=owner_id,
        group_id=group.id,
        status="DRAFT",
    )
    db.add(workflow)
    db.flush()  # autoflush=False (core/database.py) -> flush explicite pour obtenir workflow.id

    tasks_by_name: dict[str, Task] = {}
    for order_index, t in enumerate(data.tasks, start=1):
        task = Task(
            workflow_id=workflow.id,
            name=t.name,
            command=t.command,
            machine_id=machines_by_alias[t.target].id,
            order_index=order_index,
        )
        db.add(task)
        tasks_by_name[t.name] = task

    db.flush()  # un seul flush pour obtenir tous les task.id avant de résoudre les conditions

    for t in data.tasks:
        if t.condition is not None:
            task = tasks_by_name[t.name]
            task.condition_task_id = tasks_by_name[t.condition.task].id
            task.condition_expected_code = t.condition.return_code

    db.commit()
    db.refresh(workflow)
    return workflow


def list_workflows(db: Session) -> list[Workflow]:
    return db.query(Workflow).order_by(Workflow.id).all()


def get_workflow(db: Session, workflow_id: int) -> Workflow | None:
    return db.get(Workflow, workflow_id)