from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.config.settings import settings

try:
    import aio_pika
    from aio_pika.abc import AbstractChannel, AbstractExchange, AbstractRobustConnection
except ModuleNotFoundError:  # pragma: no cover - exercised only without optional deps installed
    aio_pika = None  # type: ignore[assignment]
    AbstractChannel = Any  # type: ignore[misc,assignment]
    AbstractExchange = Any  # type: ignore[misc,assignment]
    AbstractRobustConnection = Any  # type: ignore[misc,assignment]

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RabbitMQPublisherConfig:
    exchange_name: str
    exchange_type: str = "topic"
    device_routing_key_prefix: str = "device"


class RabbitMQProducer:
    """Publishes durable JSON messages to a RabbitMQ exchange."""

    def __init__(
        self,
        *,
        url: str,
        config: RabbitMQPublisherConfig,
    ) -> None:
        self._url = url
        self._config = config
        self._connection: AbstractRobustConnection | None = None
        self._channel: AbstractChannel | None = None
        self._exchange: AbstractExchange | None = None

    async def start(self) -> None:
        if aio_pika is None:
            raise RuntimeError("aio-pika is required for RabbitMQ messaging")  # noqa: TRY003
        if self.healthy:
            return

        connection = await aio_pika.connect_robust(self._url)
        channel = await connection.channel(publisher_confirms=True)

        channel.add_on_return_callback(self._on_message_returned)

        exchange = await channel.declare_exchange(
            self._config.exchange_name,
            self._exchange_type(),
            durable=True,
        )

        self._connection = connection
        self._channel = channel
        self._exchange = exchange
        logger.info("RabbitMQ producer connected to exchange '%s'", self._config.exchange_name)

    async def stop(self) -> None:
        if self._connection is not None and not self._connection.is_closed:
            await self._connection.close()
            logger.info("RabbitMQ producer disconnected")
        self._exchange = None
        self._channel = None
        self._connection = None

    @staticmethod
    async def _on_message_returned(returned_message: Any) -> None:
        logger.warning(
            "Message returned (routing_key=%s, reply_code=%s, reply_text=%s, exchange=%s)",
            getattr(returned_message, "routing_key", "?"),
            getattr(returned_message, "reply_code", "?"),
            getattr(returned_message, "reply_text", "?"),
            getattr(returned_message, "exchange", "?"),
        )

    async def _ensure_connected(self) -> None:
        if self.healthy:
            return
        if self._connection is not None:
            logger.warning("RabbitMQ producer reconnecting...")
            await self.start()

    async def publish_json(
        self,
        payload: dict[str, Any],
        *,
        routing_key: str,
        message_id: str | None = None,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> str:
        await self._ensure_connected()

        exchange = self._exchange
        if exchange is None:
            raise RuntimeError("RabbitMQ producer is not started")  # noqa: TRY003

        published_message_id = message_id or str(uuid4())
        body = json.dumps(payload, default=str, separators=(",", ":")).encode()
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            message_id=published_message_id,
            correlation_id=correlation_id,
            headers=headers,
        )
        await exchange.publish(
            message,
            routing_key=routing_key,
            mandatory=True,
        )
        return published_message_id

    async def publish_policy_deployment(
        self,
        *,
        device_id: int | str,
        policy_id: int,
        policy_name: str,
        policy_config: dict[str, Any],
        deployment_id: int | None = None,
        device_serial_number: str | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "event_type": "policy.deployment.requested",
            "device_id": device_id,
            "policy_id": policy_id,
            "policy_name": policy_name,
            "policy_config": policy_config,
        }
        if deployment_id is not None:
            payload["deployment_id"] = deployment_id
        if device_serial_number is not None:
            payload["device_serial_number"] = device_serial_number

        return await self.publish_json(
            payload,
            routing_key=self.device_routing_key(device_id),
            correlation_id=str(deployment_id or policy_id),
        )

    def device_routing_key(self, device_id: int | str) -> str:
        return f"{self._config.device_routing_key_prefix}.{device_id}"

    def _exchange_type(self) -> Any:
        try:
            return aio_pika.ExchangeType(self._config.exchange_type)
        except ValueError as err:
            raise ValueError(f"Unsupported RabbitMQ exchange type: {self._config.exchange_type}") from err

    @property
    def healthy(self) -> bool:
        return self._connection is not None and not self._connection.is_closed


rabbitmq_publisher_config = RabbitMQPublisherConfig(
    exchange_name=settings.rabbitmq_exchange,
    exchange_type=settings.rabbitmq_exchange_type,
    device_routing_key_prefix=settings.rabbitmq_device_routing_key_prefix,
)
rabbitmq_producer = RabbitMQProducer(
    url=settings.rabbitmq_url,
    config=rabbitmq_publisher_config,
)
