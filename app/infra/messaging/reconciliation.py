from __future__ import annotations

import os
from enum import StrEnum
from uuid import uuid4

from faststream.rabbit import RabbitQueue
from pydantic import BaseModel

from app.infra.messaging.broker import broker

_queue_name = os.environ.get("POD_NAME") or f"recon-{uuid4().hex[:8]}"


class RecalculationKind(StrEnum):
    PROFILE = "profile"
    MOBILE_APP = "mobile_app"


class ReconciliationRequest(BaseModel):
    entity_id: int
    force_push: bool = False


_profile_queue = RabbitQueue(f"{_queue_name}.profile")
_mobile_app_queue = RabbitQueue(f"{_queue_name}.mobile_app")

_request_queues: dict[RecalculationKind, RabbitQueue] = {
    RecalculationKind.PROFILE: _profile_queue,
    RecalculationKind.MOBILE_APP: _mobile_app_queue,
}


async def request_recalculation(kind: RecalculationKind, entity_id: int, force_push: bool = False) -> None:
    message = ReconciliationRequest(entity_id=entity_id, force_push=force_push)
    await broker.publish(message.model_dump(mode="json"), queue=_request_queues[kind])
