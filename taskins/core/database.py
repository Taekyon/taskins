from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from taskins.core.config import settings

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    """Active les clés étrangères à chaque connexion (requis par SQLite)."""
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
    """Crée toutes les tables et insère les données initiales si nécessaire."""
    from taskins import models  # noqa: F401 — enregistre les modèles auprès de Base

    Base.metadata.create_all(bind=engine)

    _seed(SessionLocal())
    _bootstrap_admin(SessionLocal())

    db = SessionLocal()
    try:
        ensure_not_last_admin(db)
    finally:
        db.close()


def _seed(db) -> None:
    """Insère les données initiales (groupe 'all', machine worker-1) si absentes."""
    from taskins.models.group import Group
    from taskins.models.machine import Machine

    try:
        if not db.query(Group).filter_by(name="all").first():
            db.add(Group(name="all"))

        if not db.query(Machine).filter_by(alias="worker-1").first():
            db.add(Machine(
                alias="worker-1",
                host="192.168.X.X",   # à corriger via l'interface d'administration
                ssh_user="svc-taskins",
                ssh_port=22,
            ))

        db.commit()
    finally:
        db.close()


def _bootstrap_admin(db) -> None:
    """Crée le premier compte admin si la table users est vide.

    Contrôlé par TASKINS_BOOTSTRAP_ADMIN_USERNAME / TASKINS_BOOTSTRAP_ADMIN_PASSWORD.
    Si la table n'est pas vide, ou si ces variables ne sont pas définies, ne fait rien.
    """
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
                "TASKINS_BOOTSTRAP_ADMIN_PASSWORD non définis — aucun compte admin créé. "
                "L'application est inaccessible tant qu'aucun utilisateur n'existe."
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


def ensure_not_last_admin(db) -> None:
    """
    Vérifie un invariant minimal sans planter si la base est vide.

    - Si aucun utilisateur n'existe, ne fait rien.
    - Si des utilisateurs existent mais aucun admin, ne fait rien ici :
      c'est le rôle de _bootstrap_admin() au démarrage ou des règles métier CRUD.
    - Si au moins un admin existe, l'état est acceptable.
    """
    from taskins.models.user import User

    user_count = db.query(User).count()
    if user_count == 0:
        return

    admin_count = db.query(User).filter_by(is_admin=1).count()
    if admin_count == 0:
        return