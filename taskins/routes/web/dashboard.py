from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.config import settings
from taskins.core.dependencies import require_user_web
from taskins.core.templates import templates
from taskins.models.user import User
from taskins.core import scheduling
from taskins.services import (
    dashboard_service,
    machine_service,
    schedule_service,
    workflow_service,
)

router = APIRouter()


@router.get("/")
def home(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    data = dashboard_service.collect(db, user)
    return templates.TemplateResponse(request, "home.html", {
        "user": user,
        "timezone": settings.timezone,
        "to_local": scheduling.sql_to_local_display,
        **data,
    })


@router.get("/workflows")
def list_workflows_page(
    request: Request,
    archived: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    workflows = workflow_service.list_workflows(db, include_archived=bool(archived))
    return templates.TemplateResponse(request, "workflows_list.html", {
        "user": user,
        "workflows": workflows,
        "show_archived": bool(archived),
    })


@router.get("/workflows/new")
def new_workflow_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    machines = machine_service.list_machines(db)
    return templates.TemplateResponse(request, "workflow_new.html", {
        "user": user,
        "machines": machines,
        "default_timeout": settings.default_task_timeout,
    })


@router.get("/workflows/{workflow_id}")
def workflow_detail_page(
    workflow_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")

    detail = workflow_service.to_workflow_detail(workflow)
    executions = sorted(workflow.executions, key=lambda e: e.id, reverse=True)

    return templates.TemplateResponse(request, "workflow_detail.html", {
        "user": user,
        "workflow": workflow,
        "tasks": detail["tasks"],
        "executions": executions,
        "machines": machine_service.list_machines(db),
        "default_timeout": settings.default_task_timeout,
        "schedules": [
            schedule_service.to_schedule_out(s)
            for s in schedule_service.list_schedules(db, workflow_id)
        ],
        "timezone": settings.timezone,
    })


@router.get("/workflows/{workflow_id}/executions/{execution_id}")
def execution_detail_page(
    workflow_id: int,
    execution_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")

    execution = next((e for e in workflow.executions if e.id == execution_id), None)
    if execution is None:
        raise HTTPException(status_code=404, detail="Exécution introuvable")

    task_results = sorted(execution.task_results, key=lambda r: r.task.order_index)

    return templates.TemplateResponse(request, "execution_detail.html", {
        "user": user,
        "workflow": workflow,
        "execution": execution,
        "task_results": task_results,
    })


@router.get("/workflows/{workflow_id}/fragments/executions")
def executions_fragment(
    workflow_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    """Fragment HTML (tbody seul) consommé par le rafraîchissement partiel.

    Rendu côté serveur plutôt que reconstruit en JavaScript : le balisage des
    lignes n'existe qu'à un seul endroit."""
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")

    executions = sorted(workflow.executions, key=lambda e: e.id, reverse=True)
    # Continuer à interroger tant qu'une exécution est en cours, ou qu'une
    # planification active peut en faire apparaître une nouvelle.
    poll = any(e.status in ("PENDING", "RUNNING") for e in executions) or any(
        s.is_active and s.next_run_at for s in workflow.schedules
    )
    return templates.TemplateResponse(request, "_executions_rows.html", {
        "workflow": workflow,
        "executions": executions,
        "poll": poll,
    })


@router.get("/workflows/{workflow_id}/executions/{execution_id}/fragments/results")
def results_fragment(
    workflow_id: int,
    execution_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    execution = next((e for e in workflow.executions if e.id == execution_id), None)
    if execution is None:
        raise HTTPException(status_code=404, detail="Exécution introuvable")

    return templates.TemplateResponse(request, "_result_rows.html", {
        "execution": execution,
        "task_results": sorted(execution.task_results, key=lambda r: r.task.order_index),
    })
