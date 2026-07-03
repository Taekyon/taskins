from pydantic import BaseModel, Field, model_validator


class ConditionIn(BaseModel):
    task: str
    return_code: int


class TaskIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    command: str = Field(min_length=1)
    target: str = Field(min_length=1)
    condition: ConditionIn | None = None


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


class ExecutionOut(BaseModel):
    id: int
    status: str
    started_at: str | None
    finished_at: str | None
