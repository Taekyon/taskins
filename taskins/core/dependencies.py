from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Charge l'utilisateur courant depuis la session, ou None si non connecté."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.get(User, user_id)


# --- Dépendances pour les routes web (redirection HTML) ---

def require_user_web(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user


def require_admin_web(user: User = Depends(require_user_web)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return user


# --- Dépendances pour les routes API (réponse JSON) ---

def require_user_api(user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Authentification requise")
    return user


def require_admin_api(user: User = Depends(require_user_api)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Droits administrateur requis")
    return user
