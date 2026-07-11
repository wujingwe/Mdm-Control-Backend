from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.messaging.consumer import RabbitMQConsumer
from app.messaging.producer import RabbitMQProducer, RabbitMQPublisherConfig


class _FakeMessage:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _FakeAioPika:
    class DeliveryMode:
        PERSISTENT = "persistent"

    class ExchangeType:
        def __init__(self, value: str):
            if value not in {"direct", "topic", "fanout", "headers"}:
                raise ValueError(value)
            self.value = value

    Message = _FakeMessage


class TestRabbitMQProducer:
    async def test_publish_json_sends_persistent_json_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = RabbitMQPublisherConfig(
            exchange_name="mdm.device.commands",
            exchange_type="topic",
            device_routing_key_prefix="device",
        )
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        exchange = SimpleNamespace(publish=AsyncMock())
        producer._exchange = exchange

        message_id = await producer.publish_json(
            {"policy_id": 1, "policy_name": "Base"},
            routing_key="device.42",
            correlation_id="1",
        )

        exchange.publish.assert_awaited_once()
        message = exchange.publish.call_args.args[0]
        assert json.loads(message.kwargs["body"].decode()) == {
            "policy_id": 1,
            "policy_name": "Base",
        }
        assert message.kwargs["content_type"] == "application/json"
        assert message.kwargs["delivery_mode"] == "persistent"
        assert message.kwargs["message_id"] == message_id
        assert message.kwargs["correlation_id"] == "1"
        assert exchange.publish.call_args.kwargs["routing_key"] == "device.42"
        assert exchange.publish.call_args.kwargs["mandatory"] is True

    async def test_publish_policy_deployment_routes_by_device_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = RabbitMQPublisherConfig(
            exchange_name="mdm.device.commands",
            exchange_type="topic",
            device_routing_key_prefix="device",
        )
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        exchange = SimpleNamespace(publish=AsyncMock())
        producer._exchange = exchange

        await producer.publish_policy_deployment(
            device_id=42,
            policy_id=10,
            policy_name="Strict",
            policy_config={"cameraDisabled": True},
            deployment_id=99,
            device_serial_number="SN001",
        )

        message = exchange.publish.call_args.args[0]
        assert json.loads(message.kwargs["body"].decode()) == {
            "event_type": "policy.deployment.requested",
            "device_id": 42,
            "policy_id": 10,
            "policy_name": "Strict",
            "policy_config": {"cameraDisabled": True},
            "deployment_id": 99,
            "device_serial_number": "SN001",
        }
        assert exchange.publish.call_args.kwargs["routing_key"] == "device.42"

    async def test_publish_requires_started_producer(self) -> None:
        producer = RabbitMQProducer(
            url="amqp://guest:guest@localhost/",
            config=RabbitMQPublisherConfig("exchange"),
        )

        with pytest.raises(RuntimeError, match="not started"):
            await producer.publish_json({"policy_id": 1}, routing_key="device.1")


class TestRabbitMQConsumer:
    def test_decode_message_requires_json_object(self) -> None:
        assert RabbitMQConsumer._decode_message(b'{"policy_id": 1}') == {"policy_id": 1}

        with pytest.raises(ValueError, match="valid JSON"):
            RabbitMQConsumer._decode_message(b"{bad")

        with pytest.raises(ValueError, match="JSON object"):
            RabbitMQConsumer._decode_message(b"[1, 2, 3]")
