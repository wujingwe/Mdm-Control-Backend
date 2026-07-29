import asyncio
import logging

from app.infra.config.settings import settings

logger = logging.getLogger(__name__)


class Lifecycle:
    def __init__(self) -> None:
        self._consumer_task: asyncio.Task | None = None

    async def start(self) -> None:
        await self._start_rabbitmq()
        if settings.rabbitmq_consumer_enabled:
            self._consumer_task = await self._start_consumer()

    async def stop(self) -> None:
        await self._stop_consumer()
        await self._stop_rabbitmq()

    @staticmethod
    async def _start_rabbitmq() -> None:
        from app.infra.messaging.producer import rabbitmq_producer

        # noinspection PyBroadException
        try:
            await rabbitmq_producer.start()
        except Exception:
            logger.warning("RabbitMQ unavailable, continuing without it")

    @staticmethod
    async def _stop_rabbitmq() -> None:
        from app.infra.messaging.producer import rabbitmq_producer

        # noinspection PyBroadException
        try:
            await rabbitmq_producer.stop()
        except Exception:
            pass

    @staticmethod
    async def _start_consumer() -> asyncio.Task:
        from app.infra.messaging.consumer import rabbitmq_consumer

        async def run_consumer() -> None:
            # noinspection PyBroadException
            try:
                await rabbitmq_consumer.run_until_stopped()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("RabbitMQ consumer unavailable, continuing without it")

        return asyncio.create_task(run_consumer())

    async def _stop_consumer(self) -> None:
        from app.infra.messaging.consumer import rabbitmq_consumer

        await rabbitmq_consumer.stop()
        if self._consumer_task is None:
            return
        self._consumer_task.cancel()
        try:
            await self._consumer_task
        except asyncio.CancelledError:
            pass
