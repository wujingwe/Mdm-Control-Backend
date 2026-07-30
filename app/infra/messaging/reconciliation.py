from __future__ import annotations

import os
from uuid import uuid4

from faststream.rabbit import RabbitQueue
from pydantic import BaseModel

from app.infra.messaging.broker import broker

_queue_name = os.environ.get("POD_NAME") or f"recon-{uuid4().hex[:8]}"
_recon_queue = RabbitQueue(_queue_name, auto_delete=True)


class ReconciliationRequest(BaseModel):
    kind: str
    entity_id: int
    force_push: bool = False


async def request_recalculation(kind: str, entity_id: int, force_push: bool = False) -> None:
    message = ReconciliationRequest(kind=kind, entity_id=entity_id, force_push=force_push)
    await broker.publish(message.model_dump(mode="json"), queue=_recon_queue)


def register_reconciliation_handler(
    handle_profile_recalculate,
    handle_mobile_app_recalculate,
) -> None:
    @broker.subscriber(_recon_queue)
    async def handle_reconciliation(message: ReconciliationRequest) -> None:
        if message.kind == "profile.recalculate":
            await handle_profile_recalculate(message.entity_id, force_push=message.force_push)
        elif message.kind == "mobile_app.recalculate":
            await handle_mobile_app_recalculate(message.entity_id, force_push=message.force_push)
