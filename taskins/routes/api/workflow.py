from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_user_api
from taskins.schemas.workflow import WorkflowCreate, WorkflowOut
from taskins.services import workflow_service

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowOut, status_code=201)
def create_workflow(
    data: WorkflowCreate,
    db: Session = Depends(get_db),
    user=Depends(require_user_api),
):
    try:
        return workflow_service.create_workflow(db, owner_id=user.id, data=data)
    except workflow_service.WorkflowValidationError as e:
        raise HTTPException(status_code=400, detail={"errors": e.errors})


@router.get("", response_model=list[WorkflowOut])
def list_workflows(db: Session = Depends(get_db), _user=Depends(require_user_api)):
    return workflow_service.list_workflows(db)


@router.get("/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: int, db: Session = Depends(get_db), _user=Depends(require_user_api)):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    return workflow