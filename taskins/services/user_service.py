from sqlalchemy.orm import Session

from taskins.core.security import hash_password
from taskins.models.user import User
from taskins.schemas.user import UserCreate


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


def set_admin(db: Session, user: User, is_admin: bool) -> User:
    user.is_admin = int(is_admin)
    db.commit()
    db.refresh(user)
    return user
