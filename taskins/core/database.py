from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from taskins.core.config import settings


engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from taskins import models  # noqa: F401 — enregistre les modèles auprès de Base

    Base.metadata.create_all(bind=engine)
    _seed(SessionLocal())
    _bootstrap_admin(SessionLocal())


def _seed(db) -> None:
    from taskins.models.group import Group
    from taskins.models.machine import Machine

    try:
        if not db.query(Group).filter_by(name="all").first():
            db.add(Group(name="all"))

        if settings.seed_machine_host:
            alias = settings.seed_machine_alias
            if not db.query(Machine).filter_by(alias=alias).first():
                db.add(Machine(
                    alias=alias,
                    host=settings.seed_machine_host,
                    ssh_user=settings.seed_machine_ssh_user,
                    ssh_port=settings.seed_machine_ssh_port,
                ))

        db.commit()
    finally:
        db.close()


def _bootstrap_admin(db) -> None:
    import logging

    from taskins.core.security import hash_password
    from taskins.models.user import User

    logger = logging.getLogger(__name__)

    try:
        if db.query(User).count() > 0:
            return

        if not settings.bootstrap_admin_username or not settings.bootstrap_admin_password:
            logger.warning(
                "Aucun utilisateur en base et TASKINS_BOOTSTRAP_ADMIN_USERNAME / "
                "TASKINS_BOOTSTRAP_ADMIN_PASSWORD non définis — aucun compte admin créé."
            )
            return

        db.add(User(
            username=settings.bootstrap_admin_username,
            password_hash=hash_password(settings.bootstrap_admin_password),
            is_admin=1,
        ))
        db.commit()
        logger.info(f"Compte admin '{settings.bootstrap_admin_username}' créé au démarrage.")
    finally:
        db.close()
