from pydantic import BaseModel, Field


class ConditionCreate(BaseModel):
    task: str = Field(min_length=1, max_length=64)
    return_code: int = Field(ge=0, le=255)  # plage standard des codes de sortie POSIX


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    command: str = Field(min_length=1, max_length=4000)
    target: str = Field(min_length=1, max_length=64)
    condition: ConditionCreate | None = None


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=2000)
    tasks: list[TaskCreate] = Field(min_length=1)


class TaskOut(BaseModel):
    id: int
    name: str
    command: str
    machine_id: int
    order_index: int
    condition_task_id: int | None
    condition_expected_code: int | None

    model_config = {"from_attributes": True}


class WorkflowOut(BaseModel):
    id: int
    name: str
    description: str | None
    owner_id: int
    group_id: int
    status: str
    tasks: list[TaskOut]

    model_config = {"from_attributes": True}