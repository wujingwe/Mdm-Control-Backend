import logging

from app.infra.messaging.broker import broker, exchange
from app.infra.messaging import reconciliation_worker  # noqa: F401  (registers the reconciliation subscribers)

logger = logging.getLogger(__name__)


class Lifecycle:
    async def start(self) -> None:
        try:
            await broker.start()
            await broker.declare_exchange(exchange)
        except Exception:
            logger.warning("RabbitMQ unavailable, continuing without it")

    async def stop(self) -> None:
        try:
            await broker.stop()
        except Exception:
            pass
