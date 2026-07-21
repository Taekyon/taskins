from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_user_api
from taskins.models.user import User
from taskins.schemas.workflow import (
    ExecutionCreate,
    ExecutionOut,
    TaskResultOut,
    WorkflowCreate,
    WorkflowDetailOut,
    WorkflowOut,
)
from taskins.services import workflow_service
from taskins.services.workflow_service import WorkflowValidationError

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


@router.get("", response_model=list[WorkflowOut])
def list_workflows(db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    return [workflow_service.to_workflow_out(w) for w in workflow_service.list_workflows(db)]


@router.post("", response_model=WorkflowDetailOut, status_code=201)
def create_workflow(
    data: WorkflowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_api),
):
    try:
        workflow = workflow_service.create_workflow(db, data, user)
    except WorkflowValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return workflow_service.to_workflow_detail(workflow)


@router.get("/{workflow_id}", response_model=WorkflowDetailOut)
def get_workflow(workflow_id: int, db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    return workflow_service.to_workflow_detail(workflow)


@router.post("/{workflow_id}/submit", response_model=WorkflowOut)
def submit_workflow(workflow_id: int, db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    try:
        workflow = workflow_service.submit_workflow(db, workflow)
    except WorkflowValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return workflow_service.to_workflow_out(workflow)


@router.post("/{workflow_id}/execute", response_model=ExecutionOut, status_code=201)
def execute_workflow(
    workflow_id: int,
    data: ExecutionCreate | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user_api),
):
    """Corps optionnel : {"machine": "worker-2"} pour rediriger toutes les
    tâches vers une autre machine (retargeting). Sans corps, chaque tâche
    utilise sa machine par défaut."""
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    try:
        execution = workflow_service.execute_workflow(
            db, workflow, machine_alias=data.machine if data else None
        )
    except WorkflowValidationError as e:
        # Machine inconnue = 422 (donnée invalide) ; mauvais statut = 409 (conflit d'état).
        status = 422 if "Machine cible inconnue" in str(e) else 409
        raise HTTPException(status_code=status, detail=str(e))
    return workflow_service.to_execution_out(execution)


@router.get("/{workflow_id}/executions", response_model=list[ExecutionOut])
def list_executions(workflow_id: int, db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    return [workflow_service.to_execution_out(e) for e in workflow.executions]


@router.get("/{workflow_id}/executions/{execution_id}/results", response_model=list[TaskResultOut])
def list_task_results(
    workflow_id: int,
    execution_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(require_user_api),
):
    """Détail des tâches d'une exécution — alimente le rafraîchissement partiel
    du frontend (étape 11) sans recharger la page."""
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    execution = next((e for e in workflow.executions if e.id == execution_id), None)
    if execution is None:
        raise HTTPException(status_code=404, detail="Exécution introuvable")
    results = sorted(execution.task_results, key=lambda r: r.task.order_index)
    return [workflow_service.to_task_result_out(r) for r in results]
