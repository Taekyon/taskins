from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_user_api
from taskins.models.user import User
from taskins.schemas.workflow import ExecutionOut, WorkflowCreate, WorkflowDetailOut, WorkflowOut
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
def execute_workflow(workflow_id: int, db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    try:
        execution = workflow_service.execute_workflow(db, workflow)
    except WorkflowValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return execution


@router.get("/{workflow_id}/executions", response_model=list[ExecutionOut])
def list_executions(workflow_id: int, db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    return workflow.executions
