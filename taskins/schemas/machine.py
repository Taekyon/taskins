from pydantic import BaseModel, Field


class MachineCreate(BaseModel):
    alias: str = Field(min_length=1, max_length=64)
    host: str = Field(min_length=1)
    ssh_user: str = "svc-taskins"
    ssh_port: int = 22


class MachineUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs fournis sont modifiés.

    L'alias est modifiable ; l'historique n'en souffre pas puisque
    `task_results` en conserve un instantané figé (étape 9)."""

    alias: str | None = Field(default=None, min_length=1, max_length=64)
    host: str | None = Field(default=None, min_length=1)
    ssh_user: str | None = Field(default=None, min_length=1)
    ssh_port: int | None = Field(default=None, gt=0, le=65535)


class MachineOut(BaseModel):
    id: int
    alias: str
    host: str
    ssh_user: str
    ssh_port: int

    model_config = {"from_attributes": True}
