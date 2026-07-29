from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.domains.commands.models import Command
from app.infra.common.enums import AssignmentStatus, CommandStatus
from app.infra.config.settings import settings
from app.infra.core.database import async_session
from app.infra.webhooks import send_validation_webhook
from app.domains.profiles.models import ProfileAssignment

try:
    import aio_pika
    from aio_pika.abc import (
        AbstractChannel,
        AbstractExchange,
        AbstractIncomingMessage,
        AbstractQueue,
        AbstractRobustConnection,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised only without optional deps installed
    aio_pika = None  # type: ignore[assignment]
    AbstractChannel = Any  # type: ignore[misc,assignment]
    AbstractExchange = Any  # type: ignore[misc,assignment]
    AbstractIncomingMessage = Any  # type: ignore[misc,assignment]
    AbstractQueue = Any  # type: ignore[misc,assignment]
    AbstractRobustConnection = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class RabbitMQConsumerConfig:
    url: str
    exchange_name: str
    queue_name: str
    exchange_type: str = "topic"
    binding_keys: tuple[str, ...] = field(default_factory=tuple)
    prefetch_count: int = 10
    requeue_on_error: bool = False


class RabbitMQConsumer:
    """Consumes JSON messages from a RabbitMQ queue owned by this consumer."""

    def __init__(
        self,
        *,
        config: RabbitMQConsumerConfig,
        handler: MessageHandler,
    ) -> None:
        self._config = config
        self._handler = handler
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None
        self._queue: AbstractQueue | None = None
        self._consumer_tag: str | None = None
        self._stopped = asyncio.Event()

    async def start(self) -> None:
        if aio_pika is None:
            raise RuntimeError("aio-pika is required for RabbitMQ messaging")  # noqa: TRY003
        if self.healthy:
            return

        connection = await aio_pika.connect_robust(self._config.url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=self._config.prefetch_count)
        exchange = await channel.declare_exchange(
            self._config.exchange_name,
            self._exchange_type(),
            durable=True,
        )
        queue = await channel.declare_queue(self._config.queue_name, durable=True)
        for binding_key in self._config.binding_keys:
            await queue.bind(exchange, routing_key=binding_key)

        self._connection = connection
        self._channel = channel
        self._exchange = exchange
        self._queue = queue
        self._consumer_tag = await queue.consume(self._on_message)
        self._stopped.clear()
        logger.info("RabbitMQ consumer listening on queue '%s'", self._config.queue_name)

    async def stop(self) -> None:
        queue = self._queue
        if queue is not None and self._consumer_tag is not None:
            await queue.cancel(self._consumer_tag)
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ consumer disconnected")

        self._consumer_tag = None
        self._queue = None
        self._exchange = None
        self._channel = None
        self._connection = None
        self._stopped.set()

    async def run_until_stopped(self) -> None:
        await self.start()
        await self._stopped.wait()

    async def bind_routing_key(self, routing_key: str) -> None:
        if self._queue is None or self._exchange is None:
            raise RuntimeError("RabbitMQ consumer is not started")  # noqa: TRY003
        await self._queue.bind(self._exchange, routing_key=routing_key)

    async def unbind_routing_key(self, routing_key: str) -> None:
        if self._queue is None or self._exchange is None:
            raise RuntimeError("RabbitMQ consumer is not started")  # noqa: TRY003
        await self._queue.unbind(self._exchange, routing_key=routing_key)

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        async with message.process(requeue=self._config.requeue_on_error):
            payload = self._decode_message(message.body)
            await self._handler(payload)

    @staticmethod
    def _decode_message(body: bytes) -> dict[str, Any]:
        try:
            payload = json.loads(body.decode())
        except (UnicodeDecodeError, json.JSONDecodeError) as err:
            raise ValueError("RabbitMQ message body must be valid JSON") from err  # noqa: TRY003
        if not isinstance(payload, dict):
            raise ValueError("RabbitMQ message body must be a JSON object")  # noqa: TRY003
        return payload

    def _exchange_type(self) -> Any:
        try:
            return aio_pika.ExchangeType(self._config.exchange_type)
        except ValueError as err:
            raise ValueError(f"Unsupported RabbitMQ exchange type: {self._config.exchange_type}") from err

    @property
    def healthy(self) -> bool:
        return self._connection is not None and not self._connection.is_closed


async def process_profile_status_message(data: dict[str, Any]) -> None:
    event_type = data.get("event_type", "")
    device_id = data.get("device_id")
    profile_id = data.get("profile_id")
    status = data.get("status")

    if event_type == "profile.status.reported":
        if not profile_id or device_id is None:
            logger.warning("Invalid profile status message: %s", data)
            return

        if status not in (
            AssignmentStatus.PENDING,
            AssignmentStatus.SENT,
            AssignmentStatus.APPLIED,
            AssignmentStatus.FAILED,
            AssignmentStatus.REVOKED,
        ):
            logger.warning("Invalid status '%s' in profile status message", status)
            return

        async with async_session() as db:
            assignment_id = data.get("assignment_id")
            if assignment_id:
                assignment = await db.get(ProfileAssignment, int(assignment_id))
            else:
                from sqlalchemy import desc

                stmt = (
                    select(ProfileAssignment)
                    .where(
                        ProfileAssignment.profile_id == int(profile_id),
                        ProfileAssignment.device_id == int(device_id),
                    )
                    .order_by(desc(ProfileAssignment.profile_version))
                    .limit(1)
                )
                result = await db.execute(stmt)
                assignment = result.scalar_one_or_none()

            reported_version = data.get("profile_version")
            if assignment and reported_version is not None and assignment.profile_version != int(reported_version):
                logger.info(
                    "Ignoring stale profile status for profile %s/device %s",
                    profile_id,
                    device_id,
                )
                return

            if assignment:
                assignment.status = status
                if status == AssignmentStatus.APPLIED:
                    from datetime import datetime, timezone

                    assignment.applied_at = datetime.now(timezone.utc)
                elif status == AssignmentStatus.REVOKED:
                    from datetime import datetime, timezone

                    assignment.revoked_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info(
                    "Profile %s assignment for device %s updated to %s",
                    profile_id,
                    device_id,
                    status,
                )
            else:
                logger.warning(
                    "No assignment found for profile %s and device %s",
                    profile_id,
                    device_id,
                )

        try:
            await send_validation_webhook(str(device_id))
        except Exception:  # noqa: BLE001 — side-effect failure must not nack the message
            logger.exception("Failed to send validation webhook for device %s", device_id)
    else:
        logger.debug("Ignoring event_type=%s", event_type)


async def process_device_command_status(data: dict[str, Any]) -> None:
    event_type = data.get("event_type", "")
    command_id = data.get("command_id")
    result_message = data.get("result_message")

    if not command_id:
        logger.warning("Missing command_id in device command status: %s", data)
        return

    valid_transitions = {
        "device.command.acknowledged": CommandStatus.ACKNOWLEDGED,
        "device.command.in_progress": CommandStatus.IN_PROGRESS,
        "device.command.completed": CommandStatus.COMPLETED,
        "device.command.failed": CommandStatus.FAILED,
    }

    target_status = valid_transitions.get(event_type)
    if target_status is None:
        logger.debug("Ignoring event_type=%s", event_type)
        return

    async with async_session() as db:
        cmd = await db.get(Command, int(command_id))
        if not cmd:
            logger.warning("Command %s not found", command_id)
            return
        cmd.status = target_status
        if result_message is not None:
            cmd.result_message = result_message
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        if target_status == CommandStatus.COMPLETED:
            cmd.completed_at = now
        elif target_status == CommandStatus.ACKNOWLEDGED:
            cmd.acknowledged_at = now
        await db.commit()
        logger.info("Command %s updated to %s", command_id, target_status.value)


async def composite_handler(data: dict[str, Any]) -> None:
    event_type = data.get("event_type", "")
    if event_type.startswith("profile."):
        await process_profile_status_message(data)
    elif event_type.startswith("device.command."):
        await process_device_command_status(data)
    else:
        logger.debug("Ignoring unknown event_type=%s", event_type)


rabbitmq_consumer = RabbitMQConsumer(
    config=RabbitMQConsumerConfig(
        url=settings.rabbitmq_url,
        exchange_name=settings.rabbitmq_exchange,
        exchange_type=settings.rabbitmq_exchange_type,
        queue_name=settings.rabbitmq_consumer_queue,
        binding_keys=tuple(settings.rabbitmq_consumer_binding_keys),
        prefetch_count=settings.rabbitmq_prefetch_count,
        requeue_on_error=settings.rabbitmq_requeue_on_error,
    ),
    handler=composite_handler,
)
