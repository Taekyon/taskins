import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from taskins.core.config import settings
from taskins.core.database import init_db
from taskins.core.engine import run_engine_loop

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

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")