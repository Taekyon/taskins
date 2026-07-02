from pathlib import Path

from fastapi.templating import Jinja2Templates

# Instance unique partagée par tous les routers — évite de recréer
# un Jinja2Templates par module.
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")
