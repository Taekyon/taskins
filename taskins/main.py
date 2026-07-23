import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from taskins.core.config import settings
from taskins.core.database import init_db
from taskins.core.engine import run_engine_loop
from taskins.routes.api import groups as api_groups
from taskins.routes.api import machines as api_machines
from taskins.routes.api import schedules as api_schedules
from taskins.routes.api import users as api_users
from taskins.routes.api import workflows as api_workflows
from taskins.routes.web import admin as web_admin
from taskins.routes.web import auth as web_auth
from taskins.routes.web import dashboard as web_dashboard

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Base de données initialisée")
    engine_task = asyncio.create_task(run_engine_loop())
    yield
    engine_task.cancel()
    try:
        await engine_task
    except asyncio.CancelledError:
        pass
    logger.info("Moteur arrêté")


app = FastAPI(title="Taskins", lifespan=lifespan)

# Session basée sur cookie signé (voir 06-controle-acces.md).
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(web_auth.router)
app.include_router(web_dashboard.router)
app.include_router(web_admin.router)
app.include_router(api_groups.router)
app.include_router(api_machines.router)
app.include_router(api_schedules.router)
app.include_router(api_users.router)
app.include_router(api_workflows.router)
