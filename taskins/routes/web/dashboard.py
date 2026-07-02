from fastapi import APIRouter, Depends, Request

from taskins.core.dependencies import require_user_web
from taskins.core.templates import templates
from taskins.models.user import User

router = APIRouter()


@router.get("/")
def home(request: Request, user: User = Depends(require_user_web)):
    # Page temporaire — remplacée à l'étape 6 par le tableau de bord réel
    # (liste des workflows visibles, F10/F11).
    return templates.TemplateResponse(request, "home.html", {"user": user})
