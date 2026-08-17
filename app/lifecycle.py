import logging

from app.infra.core.database import create_session, engine
from app.infra.messaging.broker import broker, exchange
from app.infra.messaging.reconciliation_worker import register_handlers

logger = logging.getLogger(__name__)


class Lifecycle:
    async def start(self) -> None:
        try:
            await broker.start()
            await broker.declare_exchange(exchange)
            register_handlers(create_session)
        except Exception:
            logger.warning("RabbitMQ unavailable, continuing without it")

    async def stop(self) -> None:
        try:
            await broker.stop()
        except Exception:
            pass
        await engine.dispose()
