from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.infra.messaging.producer import RabbitMQProducer
from app.domains.profiles.schemas.policy import Policy


class TestRabbitMQProducer:
    async def test_publish_profile_push_routes_by_serial(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_profile_push(
            serial_number="SER001",
            profile_id=10,
            profile_config=Policy(cameraDisabled=True),
            profile_version=3,
            assignment_id=42,
        )

        mock_publish.assert_awaited_once()
        kwargs = mock_publish.call_args.kwargs
        assert kwargs["routing_key"] == "SER001"
        assert kwargs["correlation_id"] == "10"
        body = mock_publish.call_args.args[0]
        assert body.kind == "profile.push"
        assert body.serial_number == "SER001"
        assert body.profile_id == 10
        assert body.profile_config == Policy(cameraDisabled=True)
        assert body.profile_version == 3
        assert body.assignment_id == 42

    async def test_publish_profile_revoke_routes_by_serial(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_profile_revoke(
            serial_number="SER001",
            profile_id=10,
            profile_version=3,
            assignment_id=42,
        )

        kwargs = mock_publish.call_args.kwargs
        assert kwargs["routing_key"] == "SER001"
        assert kwargs["correlation_id"] == "10"
        body = mock_publish.call_args.args[0]
        assert body.kind == "profile.revoke"
        assert body.serial_number == "SER001"
        assert body.profile_id == 10
        assert body.profile_version == 3
        assert body.assignment_id == 42

    async def test_publish_json_sends_payload(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        message_id = await producer.publish_json(
            {"profile_id": 1, "profile_name": "Base"},
            routing_key="device.42",
            correlation_id="1",
        )

        mock_publish.assert_awaited_once()
        kwargs = mock_publish.call_args.kwargs
        assert kwargs["routing_key"] == "device.42"
        assert kwargs["correlation_id"] == "1"
        assert kwargs["content_type"] == "application/json"
        assert kwargs["message_id"] == message_id
        body = mock_publish.call_args.args[0]
        assert body == {"profile_id": 1, "profile_name": "Base"}

    async def test_publish_json_generates_message_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        message_id = await producer.publish_json(
            {"key": "val"},
            routing_key="device.1",
        )

        assert isinstance(message_id, str)
        assert len(message_id) == 36

    async def test_publish_json_with_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_json(
            {"key": "val"},
            routing_key="device.1",
            headers={"x-retry-count": 3},
        )

        kwargs = mock_publish.call_args.kwargs
        assert kwargs["headers"] == {"x-retry-count": 3}

    async def test_publish_json_without_correlation_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_json({"key": "val"}, routing_key="device.1")

        kwargs = mock_publish.call_args.kwargs
        assert kwargs.get("correlation_id") is None

    async def test_publish_mobile_app_push(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_mobile_app_push(
            serial_number="SER001",
            mobile_app_id=1,
            package_name="com.example.app",
            package_version="1.0.0",
            app_version=2,
            assignment_id=100,
        )

        kwargs = mock_publish.call_args.kwargs
        assert kwargs["routing_key"] == "SER001"
        body = mock_publish.call_args.args[0]
        assert body.kind == "mobile_app.push"
        assert body.mobile_app_id == 1
        assert body.package_name == "com.example.app"

    async def test_publish_mobile_app_revoke(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_mobile_app_revoke(
            serial_number="SER001",
            mobile_app_id=1,
            package_name="com.example.app",
            app_version=2,
            assignment_id=100,
        )

        body = mock_publish.call_args.args[0]
        assert body.kind == "mobile_app.revoke"

    async def test_publish_device_command(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.producer.broker.publish", mock_publish)

        producer = RabbitMQProducer()
        await producer.publish_device_command(
            serial_number="SER001",
            command_id=1,
            command_type="LOCK",
            parameters={"reason": "lost"},
        )

        kwargs = mock_publish.call_args.kwargs
        assert kwargs["routing_key"] == "SER001"
        body = mock_publish.call_args.args[0]
        assert body.kind == "device.command"
        assert body.command_type == "LOCK"

    def test_healthy(self) -> None:
        producer = RabbitMQProducer()
        assert producer.healthy is False

    def test_uses_shared_broker_singleton(self) -> None:
        from app.infra.messaging import broker as broker_module
        from app.infra.messaging import producer as producer_module

        assert producer_module.broker is broker_module.broker
