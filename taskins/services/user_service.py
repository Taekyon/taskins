from sqlalchemy.orm import Session

from taskins.core.security import hash_password, verify_password
from taskins.models.user import User
from taskins.schemas.user import UserCreate


class UserValidationError(Exception):
    pass


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.username).all()


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, data: UserCreate) -> User:
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        is_admin=int(data.is_admin),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_password(db: Session, user: User, new_password: str) -> User:
    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)
    return user


def change_own_password(db: Session, user: User, current: str, new: str) -> User:
    if not verify_password(current, user.password_hash):
        raise UserValidationError("Mot de passe actuel incorrect")
    if current == new:
        raise UserValidationError("Le nouveau mot de passe doit être différent de l'ancien")
    return set_password(db, user, new)


def set_admin(db: Session, user: User, is_admin: bool) -> User:
    user.is_admin = int(is_admin)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User, current_user: User) -> None:
    """Trois gardes, chacune protège d'un mode de panne distinct :
    - auto-suppression : l'utilisateur se déconnecterait de force ;
    - dernier admin : plus personne ne pourrait administrer, et le bootstrap ne
      se réarme que si la table users est entièrement vide -> verrouillage ;
    - workflows possédés : workflows.owner_id interdit l'orphelin."""
    from taskins.models.workflow import Workflow

    if user.id == current_user.id:
        raise UserValidationError("Impossible de supprimer son propre compte")

    if user.is_admin:
        n_admins = db.query(User).filter(User.is_admin == 1).count()
        if n_admins <= 1:
            raise UserValidationError(
                "Impossible de supprimer le dernier administrateur : "
                "l'application deviendrait inadministrable"
            )

    n_workflows = db.query(Workflow).filter_by(owner_id=user.id).count()
    if n_workflows:
        raise UserValidationError(
            f"'{user.username}' possède encore {n_workflows} workflow(s). "
            "Les supprimer ou les archiver d'abord."
        )

    db.delete(user)
    db.commit()
