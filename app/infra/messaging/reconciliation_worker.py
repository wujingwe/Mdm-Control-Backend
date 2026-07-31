from __future__ import annotations

from app.infra.messaging.broker import broker
from app.infra.messaging.reconciliation import ReconciliationRequest, _mobile_app_queue, _profile_queue
from app.domains.devices.repositories import DeviceRepository
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.repositories import ProfileRepository
from app.domains.smart_groups.repositories import SmartGroupRepository
from app.infra.core.database import async_session
from app.infra.messaging.producer import rabbitmq_producer
from app.infra.reconciler.reconciler import AssignmentReconciler


async def _recalculate_profile(entity_id: int, *, force_push: bool = False) -> None:
    async with async_session() as db:
        reconciler = AssignmentReconciler(
            ProfileRepository(db),
            MobileAppRepository(db),
            DeviceRepository(db),
            SmartGroupRepository(db),
            rabbitmq_producer,
        )
        await reconciler.recalculate_profile(entity_id, force_push=force_push)


async def _recalculate_mobile_app(entity_id: int, *, force_push: bool = False) -> None:
    async with async_session() as db:
        reconciler = AssignmentReconciler(
            ProfileRepository(db),
            MobileAppRepository(db),
            DeviceRepository(db),
            SmartGroupRepository(db),
            rabbitmq_producer,
        )
        await reconciler.recalculate_mobile_app(entity_id, force_push=force_push)


@broker.subscriber(_profile_queue)
async def handle_profile_recalculate(message: ReconciliationRequest) -> None:
    await _recalculate_profile(message.entity_id, force_push=message.force_push)


@broker.subscriber(_mobile_app_queue)
async def handle_mobile_app_recalculate(message: ReconciliationRequest) -> None:
    await _recalculate_mobile_app(message.entity_id, force_push=message.force_push)
