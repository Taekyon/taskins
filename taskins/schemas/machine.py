from pydantic import BaseModel, Field


class MachineCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=64)
    host: str = Field(min_length=1)
    ssh_user: str = "svc-taskins"
    ssh_port: int = 22


class MachineOut(BaseModel):
    id: int
    alias: str
    host: str
    ssh_user: str
    ssh_port: int

    model_config = {"from_attributes": True}
