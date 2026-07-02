from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_admin_api
from taskins.schemas.user import UserCreate, UserOut, UserUpdate
from taskins.services import user_service

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _admin=Depends(require_admin_api)):
    return user_service.list_users(db)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_api),
):
    try:
        return user_service.create_user(db, data)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Nom d'utilisateur déjà utilisé")


@router.patch("/{user_id}", response_model=UserOut)
def update_user_admin_flag(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _admin=Depends(require_admin_api),
):
    user = user_service.get_user(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user_service.set_admin(db, user, data.is_admin)
