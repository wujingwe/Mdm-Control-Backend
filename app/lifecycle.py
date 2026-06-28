import asyncio
import logging

logger = logging.getLogger(__name__)


class Lifecycle:
    def __init__(self) -> None:
        self._consumer_task: asyncio.Task | None = None

    async def start(self) -> None:
        await self._start_kafka()
        self._consumer_task = await self._start_consumer()

    async def stop(self) -> None:
        await self._stop_consumer()
        await self._stop_kafka()

    @staticmethod
    async def _start_kafka() -> None:
        from app.messaging.producer import kafka_producer

        # noinspection PyBroadException
        try:
            await kafka_producer.start()
        except Exception:
            logger.warning("Kafka unavailable, continuing without it")

    @staticmethod
    async def _stop_kafka() -> None:
        from app.messaging.producer import kafka_producer

        # noinspection PyBroadException
        try:
            await kafka_producer.stop()
        except Exception:
            pass

    @staticmethod
    async def _start_consumer() -> asyncio.Task:
        from app.messaging.consumer import consume_policy_assignments

        return asyncio.create_task(consume_policy_assignments())

    async def _stop_consumer(self) -> None:
        if self._consumer_task is None:
            return
        self._consumer_task.cancel()
        try:
            await self._consumer_task
        except asyncio.CancelledError:
            pass
