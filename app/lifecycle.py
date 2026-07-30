import logging

from app.infra.messaging.broker import broker
from app.infra.messaging.reconciliation import register_reconciliation_handler

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


class Lifecycle:
    async def start(self) -> None:
        register_reconciliation_handler(
            handle_profile_recalculate=_recalculate_profile,
            handle_mobile_app_recalculate=_recalculate_mobile_app,
        )

        try:
            await broker.start()
        except Exception:
            logger.warning("RabbitMQ unavailable, continuing without it")

    async def stop(self) -> None:
        try:
            await broker.stop()
        except Exception:
            pass
