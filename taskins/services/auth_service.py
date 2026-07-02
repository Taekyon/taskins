from sqlalchemy.orm import Session

from taskins.core.security import verify_password
from taskins.models.user import User


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter_by(username=username).first()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
