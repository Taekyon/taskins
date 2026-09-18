from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_user_api
from taskins.models.user import User
from taskins.schemas.schedule import ScheduleCreate, ScheduleOut, ScheduleUpdate
from taskins.services import schedule_service, workflow_service
from taskins.services.schedule_service import ScheduleValidationError

router = APIRouter(tags=["schedules"])


def _owned_or_admin(schedule, user: User):
    if schedule.owner_id != user.id and not user.is_admin:
        raise HTTPException(status_code=403, detail="Seul le propriétaire ou un administrateur")


@router.get("/api/v1/workflows/{workflow_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(workflow_id: int, db: Session = Depends(get_db), _user: User = Depends(require_user_api)):
    if workflow_service.get_workflow(db, workflow_id) is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    return [schedule_service.to_schedule_out(s) for s in schedule_service.list_schedules(db, workflow_id)]


@router.post("/api/v1/workflows/{workflow_id}/schedules", response_model=ScheduleOut, status_code=201)
def create_schedule(
    workflow_id: int,
    data: ScheduleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_api),
):
    workflow = workflow_service.get_workflow(db, workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow introuvable")
    try:
        schedule = schedule_service.create_schedule(
            db, workflow, user,
            kind=data.kind,
            run_at_local=data.run_at,
            cron_expression=data.cron_expression,
            machine_alias=data.machine,
        )
    except ScheduleValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return schedule_service.to_schedule_out(schedule)


@router.patch("/api/v1/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    data: ScheduleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user_api),
):
    schedule = schedule_service.get_schedule(db, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Planification introuvable")
    _owned_or_admin(schedule, user)
    try:
        schedule = schedule_service.set_active(db, schedule, data.is_active)
    except ScheduleValidationError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return schedule_service.to_schedule_out(schedule)


@router.delete("/api/v1/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db), user: User = Depends(require_user_api)):
    schedule = schedule_service.get_schedule(db, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Planification introuvable")
    _owned_or_admin(schedule, user)
    schedule_service.delete_schedule(db, schedule)
