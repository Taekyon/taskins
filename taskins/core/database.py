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
                ssh_user="scheduler",
                ssh_port=22,
            ))

        db.commit()
    finally:
        db.close()


