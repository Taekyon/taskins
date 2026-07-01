import asyncio
import logging

from taskins.core.config import settings

logger = logging.getLogger(__name__)


async def run_engine_loop() -> None:
    """Boucle principale du moteur d'ordonnancement. Implémentée à l'étape 5."""
    while True:
        try:
            pass  # TODO: scan_and_process_pending_executions()
        except Exception as e:
            logger.error(f"Erreur dans le cycle du moteur : {e}")
        await asyncio.sleep(settings.scheduler_interval)
