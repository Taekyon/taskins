from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_user_web
from taskins.core.templates import templates
from taskins.models.user import User
from taskins.services import workflow_service

router = APIRouter()


@router.get("/")
def home(_user: User = Depends(require_user_web)):
    return RedirectResponse(url="/workflows", status_code=303)


@router.get("/workflows")
def list_workflows_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_web),
):
    workflows = workflow_service.list_workflows(db)
    return templates.TemplateResponse(request, "workflows_list.html", {
        "user": user,
        "workflows": workflows,
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
