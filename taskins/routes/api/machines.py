from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_admin_api, require_user_api
from taskins.schemas.machine import MachineCreate, MachineOut
from taskins.services import machine_service
from taskins.services.machine_service import MachineValidationError

router = APIRouter(prefix="/api/v1/machines", tags=["machines"])


@router.get("", response_model=list[MachineOut])
def list_machines(db: Session = Depends(get_db), _user=Depends(require_user_api)):
    return machine_service.list_machines(db)


@router.post("", response_model=MachineOut, status_code=201)
def create_machine(
    data: MachineCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_api),
):
    try:
        return machine_service.create_machine(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Alias déjà utilisé")


@router.delete("/{machine_id}", status_code=204)
def delete_machine(machine_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin_api)):
    machine = machine_service.get_machine(db, machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine introuvable")
    try:
        machine_service.delete_machine(db, machine)
    except MachineValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))