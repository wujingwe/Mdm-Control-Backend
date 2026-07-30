from __future__ import annotations

import asyncio
import logging
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.infra.messaging.broker import broker
from app.infra.messaging.reconciliation import register_reconciliation_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _recalculate_profile(entity_id: int, *, force_push: bool = False) -> None:
    from app.domains.mobile_apps.repositories import MobileAppRepository
    from app.domains.profiles.repositories import ProfileRepository
    from app.infra.core.database import async_session
    from app.infra.messaging.producer import rabbitmq_producer
    from app.infra.reconciler.reconciler import AssignmentReconciler

    async with async_session() as db:
        reconciler = AssignmentReconciler(ProfileRepository(db), MobileAppRepository(db), rabbitmq_producer)
        await reconciler.recalculate_profile(entity_id, force_push=force_push)


async def _recalculate_mobile_app(entity_id: int, *, force_push: bool = False) -> None:
    from app.domains.mobile_apps.repositories import MobileAppRepository
    from app.domains.profiles.repositories import ProfileRepository
    from app.infra.core.database import async_session
    from app.infra.messaging.producer import rabbitmq_producer
    from app.infra.reconciler.reconciler import AssignmentReconciler

    async with async_session() as db:
        reconciler = AssignmentReconciler(ProfileRepository(db), MobileAppRepository(db), rabbitmq_producer)
        await reconciler.recalculate_mobile_app(entity_id, force_push=force_push)


@asynccontextmanager
async def worker_lifespan() -> AsyncGenerator[None, None]:
    register_reconciliation_handler(
        handle_profile_recalculate=_recalculate_profile,
        handle_mobile_app_recalculate=_recalculate_mobile_app,
    )
    await broker.start()
    try:
        yield
    finally:
        await broker.stop()


async def main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stop_event.set)

    async with worker_lifespan():
        logger.info("Reconciliation worker started")
        await stop_event.wait()
        logger.info("Reconciliation worker stopping")


if __name__ == "__main__":
    asyncio.run(main())
