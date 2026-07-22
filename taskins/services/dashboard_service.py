"""Requêtes d'agrégation de la page d'accueil.

Aucune donnée nouvelle : uniquement des vues transverses sur les tables
existantes. Les volumes visés (quelques workflows par jour) rendent inutile
tout index ou cache supplémentaire.
"""

from datetime import timedelta

from sqlalchemy.orm import Session

from taskins.core import scheduling
from taskins.models.execution import Execution
from taskins.models.schedule import Schedule
from taskins.models.workflow import Workflow


def _since(hours: int) -> str:
    return scheduling.to_sql(scheduling.now_utc() - timedelta(hours=hours))


def collect(db: Session, user, window_hours: int = 24) -> dict:
    since = _since(window_hours)

    recent = (
        db.query(Execution)
        .filter(Execution.created_at >= since)
        .all()
    )

    return {
        "window_hours": window_hours,
        "counts": {
            "workflows": db.query(Workflow).filter(Workflow.archived_at.is_(None)).count(),
            "schedules": db.query(Schedule).filter(Schedule.is_active == 1).count(),
            "executions": len(recent),
            "failures": len([e for e in recent if e.status == "FAILED"]),
            "running": db.query(Execution).filter(Execution.status.in_(["PENDING", "RUNNING"])).count(),
        },
        # Brouillons de l'utilisateur : en V1 l'approbation admin (F3) est
        # différée, la file d'attente de validation est donc toujours vide —
        # ce sont les brouillons qui attendent une action de leur propriétaire.
        "drafts": (
            db.query(Workflow)
            .filter(Workflow.owner_id == user.id, Workflow.status == "DRAFT")
            .filter(Workflow.archived_at.is_(None))
            .order_by(Workflow.created_at.desc())
            .limit(5)
            .all()
        ),
        "my_workflows": (
            db.query(Workflow)
            .filter(Workflow.owner_id == user.id, Workflow.archived_at.is_(None))
            .order_by(Workflow.created_at.desc())
            .limit(5)
            .all()
        ),
        "next_schedules": (
            db.query(Schedule)
            .filter(Schedule.is_active == 1, Schedule.next_run_at.isnot(None))
            .order_by(Schedule.next_run_at)
            .limit(5)
            .all()
        ),
        "recent_executions": (
            db.query(Execution).order_by(Execution.id.desc()).limit(8).all()
        ),
        "recent_failures": (
            db.query(Execution)
            .filter(Execution.status == "FAILED")
            .order_by(Execution.id.desc())
            .limit(5)
            .all()
        ),
    }
