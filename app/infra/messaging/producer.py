from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from app.domains.profiles.schemas.policy import Policy
from app.infra.messaging.broker import broker, exchange
from app.infra.messaging.schemas import (
    DeviceCommandRequested,
    MobileAppPushRequested,
    MobileAppRevokeRequested,
    ProfilePushRequested,
    ProfileRevokeRequested,
)

logger = logging.getLogger(__name__)


class RabbitMQProducer:
    """Publishes messages to the SSE server exchange via the shared FastStream broker."""

    @staticmethod
    async def publish_json(
        payload: dict[str, Any],
        *,
        routing_key: str,
        message_id: str | None = None,
        correlation_id: str | None = None,
        headers: dict[str, Any] | None = None,
    ) -> str:
        published_message_id = message_id or str(uuid4())
        await broker.publish(
            payload,
            routing_key=routing_key,
            exchange=exchange,
            message_id=published_message_id,
            correlation_id=correlation_id,
            headers=headers,
            content_type="application/json",
        )
        return published_message_id

    @staticmethod
    async def publish_profile_push(
        *,
        serial_number: str,
        profile_id: int,
        profile_config: Policy,
        profile_version: int,
        assignment_id: int,
    ) -> str:
        message = ProfilePushRequested(
            serial_number=serial_number,
            profile_id=profile_id,
            profile_config=profile_config,
            profile_version=profile_version,
            assignment_id=assignment_id,
        )
        message_id = str(uuid4())
        await broker.publish(
            message,
            routing_key=serial_number,
            exchange=exchange,
            message_id=message_id,
            correlation_id=str(profile_id),
        )
        return message_id

    @staticmethod
    async def publish_profile_revoke(
        *,
        serial_number: str,
        profile_id: int,
        profile_version: int,
        assignment_id: int,
    ) -> str:
        message = ProfileRevokeRequested(
            serial_number=serial_number,
            profile_id=profile_id,
            profile_version=profile_version,
            assignment_id=assignment_id,
        )
        message_id = str(uuid4())
        await broker.publish(
            message,
            routing_key=serial_number,
            exchange=exchange,
            message_id=message_id,
            correlation_id=str(profile_id),
        )
        return message_id

    @staticmethod
    async def publish_mobile_app_push(
        *,
        serial_number: str,
        mobile_app_id: int,
        package_name: str,
        package_version: str,
        app_version: int,
        assignment_id: int,
    ) -> str:
        message = MobileAppPushRequested(
            serial_number=serial_number,
            mobile_app_id=mobile_app_id,
            package_name=package_name,
            package_version=package_version,
            app_version=app_version,
            assignment_id=assignment_id,
        )
        message_id = str(uuid4())
        await broker.publish(
            message,
            routing_key=serial_number,
            exchange=exchange,
            message_id=message_id,
            correlation_id=str(mobile_app_id),
        )
        return message_id

    @staticmethod
    async def publish_mobile_app_revoke(
        *,
        serial_number: str,
        mobile_app_id: int,
        package_name: str,
        app_version: int,
        assignment_id: int,
    ) -> str:
        message = MobileAppRevokeRequested(
            serial_number=serial_number,
            mobile_app_id=mobile_app_id,
            package_name=package_name,
            app_version=app_version,
            assignment_id=assignment_id,
        )
        message_id = str(uuid4())
        await broker.publish(
            message,
            routing_key=serial_number,
            exchange=exchange,
            message_id=message_id,
            correlation_id=str(mobile_app_id),
        )
        return message_id

    @staticmethod
    async def publish_device_command(
        *,
        serial_number: str,
        command_id: int,
        command_type: str,
        parameters: dict[str, Any],
    ) -> str:
        message = DeviceCommandRequested(
            serial_number=serial_number,
            command_id=command_id,
            command_type=command_type,
            parameters=parameters,
        )
        message_id = str(uuid4())
        await broker.publish(
            message,
            routing_key=serial_number,
            exchange=exchange,
            message_id=message_id,
            correlation_id=str(command_id),
        )
        return message_id

    @property
    def healthy(self) -> bool:
        return broker._channel is not None


rabbitmq_producer = RabbitMQProducer()
