from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from taskins.core.database import get_db
from taskins.core.dependencies import require_admin_web
from taskins.core.templates import templates
from taskins.models.user import User
from taskins.services import group_service, machine_service, user_service

router = APIRouter()


@router.get("/admin")
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin_web),
):
    return templates.TemplateResponse(request, "admin.html", {
        "user": user,
        "users": user_service.list_users(db),
        "machines": machine_service.list_machines(db),
        "groups": group_service.list_groups(db),
        "protected_group": group_service.PROTECTED_GROUP,
    })
