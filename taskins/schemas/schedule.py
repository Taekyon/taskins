from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ScheduleCreate(BaseModel):
    kind: Literal["ONCE", "CRON"]
    # ONCE : date/heure locale, 'AAAA-MM-JJ HH:MM' ou 'AAAA-MM-JJTHH:MM'
    run_at: str | None = None
    # CRON : expression à 5 champs, interprétée dans TASKINS_TIMEZONE
    cron_expression: str | None = None
    # Alias d'une machine cible, hérité par les exécutions produites
    machine: str | None = None

    @model_validator(mode="after")
    def _check_fields(self):
        if self.kind == "ONCE" and not self.run_at:
            raise ValueError("'run_at' est requis pour une planification ponctuelle")
        if self.kind == "CRON" and not self.cron_expression:
            raise ValueError("'cron_expression' est requise pour une planification récurrente")
        return self


class ScheduleUpdate(BaseModel):
    is_active: bool


class ScheduleOut(BaseModel):
    id: int
    workflow_id: int
    kind: str
    cron_expression: str | None
    target_machine: str | None
    next_run_at: str | None = Field(default=None, description="Heure locale")
    last_run_at: str | None = Field(default=None, description="Heure locale")
    is_active: bool
    owner_id: int
