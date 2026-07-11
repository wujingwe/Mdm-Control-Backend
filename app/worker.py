from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.messaging.consumer import rabbitmq_consumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def worker_lifespan() -> AsyncGenerator[None, None]:
    await rabbitmq_consumer.start()
    try:
        yield
    finally:
        await rabbitmq_consumer.stop()


async def main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop_event.set)

    async with worker_lifespan():
        logger.info("RabbitMQ worker started")
        await stop_event.wait()
        logger.info("RabbitMQ worker stopping")


if __name__ == "__main__":
    asyncio.run(main())
