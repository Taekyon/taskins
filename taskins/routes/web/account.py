from fastapi import APIRouter, Depends, Request

from taskins.core.dependencies import require_user_web
from taskins.core.templates import templates
from taskins.models.user import User

router = APIRouter()


@router.get("/account")
def account_page(request: Request, user: User = Depends(require_user_web)):
    return templates.TemplateResponse(request, "account.html", {"user": user})
