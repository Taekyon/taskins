from pydantic import BaseModel, Field, model_validator


class ConditionIn(BaseModel):
    task: str
    return_code: int


class TaskIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    command: str = Field(min_length=1)
    target: str = Field(min_length=1)
    condition: ConditionIn | None = None
    # None = repli sur TASKINS_DEFAULT_TASK_TIMEOUT
    timeout_seconds: int | None = Field(default=None, gt=0)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    tasks: list[TaskIn] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_tasks(self):
        # Règles reprises telles quelles de 08-format-yaml.md, appliquées au JSON.
        seen = set()
        for task in self.tasks:
            if task.name in seen:
                raise ValueError(f"Nom de tâche dupliqué : '{task.name}'")
            seen.add(task.name)

        names_before = set()
        for task in self.tasks:
            if task.condition is not None:
                if task.condition.task not in names_before:
                    raise ValueError(
                        f"Condition de '{task.name}' doit référencer une tâche antérieure "
                        f"dans la liste (reçu : '{task.condition.task}')"
                    )
            names_before.add(task.name)
        return self


class ConditionOut(BaseModel):
    task: str
    return_code: int


class TaskOut(BaseModel):
    id: int
    name: str
    command: str
    target: str
    order_index: int
    condition: ConditionOut | None = None
    timeout_seconds: int | None = None


class WorkflowOut(BaseModel):
    id: int
    name: str
    description: str | None
    status: str
    owner_id: int
    group_id: int
    created_at: str


class WorkflowDetailOut(WorkflowOut):
    tasks: list[TaskOut]


class ExecutionCreate(BaseModel):
    """Corps optionnel de POST /workflows/{id}/execute.

    `machine` : alias d'une machine cible qui remplace, pour cette exécution
    uniquement, la machine par défaut de chaque tâche (retargeting, option B).
    Absent ou null = chaque tâche garde sa machine par défaut."""

    machine: str | None = None


class ExecutionOut(BaseModel):
    id: int
    status: str
    started_at: str | None
    finished_at: str | None
    # Alias de la machine de retargeting, None si aucune redirection.
    target_machine: str | None = None


class TaskResultOut(BaseModel):
    id: int
    task_name: str
    status: str
    return_code: int | None
    command: str | None
    machine_alias: str | None
    machine_host: str | None
    stdout: str | None
    stderr: str | None
    started_at: str | None
    finished_at: str | None
