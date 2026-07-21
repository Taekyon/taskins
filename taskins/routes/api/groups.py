from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_admin_api, require_user_api
from taskins.schemas.group import GroupCreate, GroupOut
from taskins.services import group_service
from taskins.services.group_service import GroupValidationError

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


@router.get("", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db), _user=Depends(require_user_api)):
    return group_service.list_groups(db)


@router.post("", response_model=GroupOut, status_code=201)
def create_group(data: GroupCreate, db: Session = Depends(get_db), _admin=Depends(require_admin_api)):
    try:
        return group_service.create_group(db, data.name)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Nom de groupe déjà utilisé")


@router.delete("/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db), _admin=Depends(require_admin_api)):
    group = group_service.get_group(db, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Groupe introuvable")
    try:
        group_service.delete_group(db, group)
    except GroupValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))
