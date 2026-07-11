from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config.settings import settings
from app.database import async_session
from app.models.device import Device
from app.models.policy import Policy
from app.notification.webhook import send_validation_webhook

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


async def process_policy_deployment_message(data: dict[str, Any]) -> None:
    device_id = data.get("device_id")
    device_serial = data.get("device_serial_number")
    policy_id = data.get("policy_id")

    if not policy_id or (device_id is None and device_serial is None):
        logger.warning("Invalid policy deployment message: %s", data)
        return

    async with async_session() as db:
        device_stmt = select(Device).options(selectinload(Device.policies))
        if device_id is not None:
            device_stmt = device_stmt.where(Device.id == int(device_id))
        else:
            device_stmt = device_stmt.where(Device.serial_number == device_serial)

        device_result = await db.execute(device_stmt)
        device = device_result.scalar_one_or_none()

        if not device:
            logger.warning("Device %s not found, skipping deployment", device_id or device_serial)
            return

        policy_stmt = select(Policy).where(Policy.id == policy_id)
        policy_result = await db.execute(policy_stmt)
        policy = policy_result.scalar_one_or_none()

        if not policy:
            logger.warning("Policy %s not found, skipping deployment", policy_id)
            return

        if policy not in device.policies:
            device.policies.append(policy)
        device.connection_status = "configured"
        await db.commit()

    logger.info("Device %s updated with policy %s", device.id, policy_id)

    try:
        from app.notification.sse import notify_sse_server

        await notify_sse_server(
            device_serial=device.serial_number,
            device_name=data.get("device_name"),
            policy_id=policy_id,
            policy_name=data.get("policy_name"),
            policy_config=data.get("policy_config"),
        )
    except Exception:  # noqa: BLE001 — side-effect failure must not nack the message
        logger.exception("Failed to notify SSE server for device %s", device.id)

    try:
        await send_validation_webhook(device.serial_number)
    except Exception:  # noqa: BLE001 — side-effect failure must not nack the message
        logger.exception("Failed to send validation webhook for device %s", device.id)


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
    handler=process_policy_deployment_message,
)
