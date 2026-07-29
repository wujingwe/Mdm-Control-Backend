from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infra.messaging.consumer import (
    RabbitMQConsumer,
    RabbitMQConsumerConfig,
    process_profile_status_message,
)
from app.infra.messaging.producer import RabbitMQProducer, RabbitMQPublisherConfig


class _FakeMessage:
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class _FakeAioPika:
    class DeliveryMode:
        PERSISTENT = "persistent"

    class ExchangeType:
        def __init__(self, value: str) -> None:
            if value not in {"direct", "topic", "fanout", "headers"}:
                raise ValueError(value)
            self.value = value

    Message = _FakeMessage

    @staticmethod
    async def connect_robust(url: str) -> SimpleNamespace:
        channel = SimpleNamespace(
            publisher_confirms=True,
            add_on_return_callback=MagicMock(),
            declare_exchange=AsyncMock(),
            declare_queue=AsyncMock(),
            set_qos=AsyncMock(),
        )
        connection = SimpleNamespace(
            channel=AsyncMock(return_value=channel),
            is_closed=False,
            close=AsyncMock(),
        )
        connection._channel_instance = channel
        return connection


def _make_producer_config(**overrides: Any) -> RabbitMQPublisherConfig:
    defaults = {
        "exchange_name": "mdm.device.commands",
        "exchange_type": "topic",
        "device_routing_key_prefix": "device",
    }
    defaults.update(overrides)
    return RabbitMQPublisherConfig(**defaults)


def _make_consumer_config(**overrides: Any) -> RabbitMQConsumerConfig:
    defaults = {
        "url": "amqp://guest:guest@localhost/",
        "exchange_name": "mdm.device.commands",
        "queue_name": "mdm.test.queue",
        "exchange_type": "topic",
        "binding_keys": ("device.#",),
        "prefetch_count": 10,
        "requeue_on_error": False,
    }
    defaults.update(overrides)
    return RabbitMQConsumerConfig(**defaults)


def _make_mock_exchange() -> SimpleNamespace:
    return SimpleNamespace(publish=AsyncMock())


def _make_mock_queue() -> SimpleNamespace:
    queue = SimpleNamespace(
        bind=AsyncMock(),
        unbind=AsyncMock(),
        consume=AsyncMock(return_value="consumer-tag-123"),
        cancel=AsyncMock(),
    )
    return queue


class TestRabbitMQProducer:
    async def test_publish_json_sends_persistent_json_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        exchange = _make_mock_exchange()
        producer._exchange = exchange

        message_id = await producer.publish_json(
            {"profile_id": 1, "profile_name": "Base"},
            routing_key="device.42",
            correlation_id="1",
        )

        exchange.publish.assert_awaited_once()
        message = exchange.publish.call_args.args[0]
        assert json.loads(message.kwargs["body"].decode()) == {
            "profile_id": 1,
            "profile_name": "Base",
        }
        assert message.kwargs["content_type"] == "application/json"
        assert message.kwargs["delivery_mode"] == "persistent"
        assert message.kwargs["message_id"] == message_id
        assert message.kwargs["correlation_id"] == "1"
        assert exchange.publish.call_args.kwargs["routing_key"] == "device.42"
        assert exchange.publish.call_args.kwargs["mandatory"] is True

    async def test_publish_json_generates_message_id_when_not_provided(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._exchange = _make_mock_exchange()

        message_id = await producer.publish_json(
            {"key": "val"},
            routing_key="device.1",
        )

        assert isinstance(message_id, str)
        assert len(message_id) == 36

    async def test_publish_json_with_headers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._exchange = _make_mock_exchange()

        await producer.publish_json(
            {"key": "val"},
            routing_key="device.1",
            headers={"x-retry-count": 3},
        )

        message = producer._exchange.publish.call_args.args[0]
        assert message.kwargs["headers"] == {"x-retry-count": 3}

    async def test_publish_json_without_correlation_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._exchange = _make_mock_exchange()

        await producer.publish_json({"key": "val"}, routing_key="device.1")

        message = producer._exchange.publish.call_args.args[0]
        assert message.kwargs["correlation_id"] is None

    async def test_publish_requires_started_producer(self) -> None:
        producer = RabbitMQProducer(
            url="amqp://guest:guest@localhost/",
            config=_make_producer_config(),
        )

        with pytest.raises(RuntimeError, match="not started"):
            await producer.publish_json({"profile_id": 1}, routing_key="device.1")

    async def test_publish_profile_push_routes_by_device_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        exchange = _make_mock_exchange()
        producer._exchange = exchange

        await producer.publish_profile_push(
            device_id=42,
            profile_id=10,
            profile_config={"cameraDisabled": True},
        )

        message = exchange.publish.call_args.args[0]
        assert json.loads(message.kwargs["body"].decode()) == {
            "event_type": "profile.push.requested",
            "device_id": 42,
            "profile_id": 10,
            "profile_config": {"cameraDisabled": True},
        }
        assert exchange.publish.call_args.kwargs["routing_key"] == "device.42"
        assert message.kwargs["correlation_id"] == "10"

    async def test_publish_profile_revoke_routes_by_device_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        exchange = _make_mock_exchange()
        producer._exchange = exchange

        await producer.publish_profile_revoke(
            device_id=42,
            profile_id=10,
        )

        message = exchange.publish.call_args.args[0]
        payload = json.loads(message.kwargs["body"].decode())
        assert payload == {
            "event_type": "profile.revoke.requested",
            "device_id": 42,
            "profile_id": 10,
        }
        assert message.kwargs["correlation_id"] == "10"

    async def test_start_connects_and_declares_exchange(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        mock_exchange = _make_mock_exchange()

        async def fake_connect_robust(url: str) -> SimpleNamespace:
            channel = SimpleNamespace(
                publisher_confirms=True,
                add_on_return_callback=MagicMock(),
                declare_exchange=AsyncMock(return_value=mock_exchange),
            )
            return SimpleNamespace(
                channel=AsyncMock(return_value=channel),
                is_closed=False,
                close=AsyncMock(),
            )

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect_robust)

        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        await producer.start()

        assert producer._connection is not None
        assert producer._exchange is mock_exchange
        assert producer.healthy

    async def test_start_skips_if_already_connected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)

        connect_called = False

        async def fake_connect(url: str) -> SimpleNamespace:
            nonlocal connect_called
            connect_called = True
            return SimpleNamespace()

        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect)

        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._connection = SimpleNamespace(is_closed=False)

        await producer.start()
        assert not connect_called

    async def test_stop_closes_connection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)

        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        mock_conn = SimpleNamespace(is_closed=False, close=AsyncMock())
        producer._connection = mock_conn
        producer._channel = SimpleNamespace()
        producer._exchange = SimpleNamespace()

        await producer.stop()

        mock_conn.close.assert_awaited_once()
        assert producer._connection is None
        assert producer._channel is None
        assert producer._exchange is None

    async def test_stop_skips_if_no_connection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)

        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        await producer.stop()
        assert producer._connection is None

    async def test_stop_skips_if_already_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)

        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        mock_conn = SimpleNamespace(is_closed=True, close=AsyncMock())
        producer._connection = mock_conn

        await producer.stop()
        mock_conn.close.assert_not_called()
        assert producer._connection is None

    async def test_healthy_returns_false_when_not_connected(self) -> None:
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        assert not producer.healthy

    async def test_healthy_returns_false_when_connection_closed(self) -> None:
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._connection = SimpleNamespace(is_closed=True)
        assert not producer.healthy

    async def test_healthy_returns_true_when_connected(self) -> None:
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._connection = SimpleNamespace(is_closed=False)
        assert producer.healthy

    def test_device_routing_key(self) -> None:
        config = _make_producer_config(device_routing_key_prefix="cmd")
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        assert producer.device_routing_key(42) == "cmd.42"
        assert producer.device_routing_key("abc") == "cmd.abc"

    def test_exchange_type_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config(exchange_type="fanout")
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        result = producer._exchange_type()
        assert result.value == "fanout"

    def test_exchange_type_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config(exchange_type="invalid_type")
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        with pytest.raises(ValueError, match="Unsupported"):
            producer._exchange_type()

    async def test_start_raises_when_aio_pika_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", None)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        with pytest.raises(RuntimeError, match="aio-pika is required"):
            await producer.start()

    async def test_on_message_returned(self) -> None:
        msg = SimpleNamespace(
            routing_key="device.1",
            reply_code=312,
            reply_text="NO_ROUTE",
            exchange="mdm.device.commands",
        )
        await RabbitMQProducer._on_message_returned(msg)

    async def test_ensure_connected_reconnects_when_connection_exists_but_unhealthy(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import app.infra.messaging.producer as producer_module

        mock_exchange = _make_mock_exchange()

        async def fake_connect(url: str) -> SimpleNamespace:
            channel = SimpleNamespace(
                publisher_confirms=True,
                add_on_return_callback=MagicMock(),
                declare_exchange=AsyncMock(return_value=mock_exchange),
            )
            return SimpleNamespace(
                channel=AsyncMock(return_value=channel),
                is_closed=False,
                close=AsyncMock(),
            )

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect)

        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._connection = SimpleNamespace(is_closed=True)

        await producer._ensure_connected()
        assert producer.healthy

    async def test_publish_json_serializes_datetime_as_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from datetime import datetime

        import app.infra.messaging.producer as producer_module

        monkeypatch.setattr(producer_module, "aio_pika", _FakeAioPika)
        config = _make_producer_config()
        producer = RabbitMQProducer(url="amqp://guest:guest@localhost/", config=config)
        producer._exchange = _make_mock_exchange()

        ts = datetime(2025, 1, 15, 10, 30, 0)
        await producer.publish_json(
            {"timestamp": ts},
            routing_key="device.1",
        )

        message = producer._exchange.publish.call_args.args[0]
        payload = json.loads(message.kwargs["body"].decode())
        assert "2025-01-15" in payload["timestamp"]


class TestRabbitMQConsumer:
    def test_decode_message_valid(self) -> None:
        assert RabbitMQConsumer._decode_message(b'{"profile_id": 1}') == {"profile_id": 1}

    def test_decode_message_invalid_json(self) -> None:
        with pytest.raises(ValueError, match="valid JSON"):
            RabbitMQConsumer._decode_message(b"{bad")

    def test_decode_message_not_object(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            RabbitMQConsumer._decode_message(b"[1, 2, 3]")

    def test_decode_message_not_dict(self) -> None:
        with pytest.raises(ValueError, match="JSON object"):
            RabbitMQConsumer._decode_message(b'"just a string"')

    async def test_start_connects_declares_exchange_queue_and_consumes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        mock_exchange = _make_mock_exchange()
        mock_queue = _make_mock_queue()

        async def fake_connect(url: str) -> SimpleNamespace:
            channel = SimpleNamespace(
                declare_exchange=AsyncMock(return_value=mock_exchange),
                declare_queue=AsyncMock(return_value=mock_queue),
                set_qos=AsyncMock(),
            )
            return SimpleNamespace(
                channel=AsyncMock(return_value=channel),
                is_closed=False,
                close=AsyncMock(),
            )

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)
        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect)

        config = _make_consumer_config(binding_keys=("device.#",))
        handler = AsyncMock()
        consumer = RabbitMQConsumer(config=config, handler=handler)
        await consumer.start()

        assert consumer._connection is not None
        assert consumer._exchange is mock_exchange
        assert consumer._queue is mock_queue
        mock_queue.bind.assert_awaited_once_with(mock_exchange, routing_key="device.#")
        mock_queue.consume.assert_awaited_once()
        assert consumer._consumer_tag == "consumer-tag-123"
        assert consumer.healthy

    async def test_start_sets_qos(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        mock_exchange = _make_mock_exchange()
        mock_queue = _make_mock_queue()
        set_qos_called_with = {}

        async def fake_connect(url: str) -> SimpleNamespace:
            channel = SimpleNamespace(
                declare_exchange=AsyncMock(return_value=mock_exchange),
                declare_queue=AsyncMock(return_value=mock_queue),
                set_qos=AsyncMock(side_effect=lambda **kw: set_qos_called_with.update(kw)),
            )
            return SimpleNamespace(
                channel=AsyncMock(return_value=channel),
                is_closed=False,
                close=AsyncMock(),
            )

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)
        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect)

        config = _make_consumer_config(prefetch_count=25)
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        await consumer.start()

        assert set_qos_called_with == {"prefetch_count": 25}

    async def test_start_skips_if_already_connected(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        connect_called = False

        async def fake_connect(url: str) -> SimpleNamespace:
            nonlocal connect_called
            connect_called = True
            return SimpleNamespace()

        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect)

        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        consumer._connection = SimpleNamespace(is_closed=False)

        await consumer.start()
        assert not connect_called

    async def test_stop_cancels_consumer_and_closes_connection(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())

        mock_queue = SimpleNamespace(cancel=AsyncMock())
        mock_conn = SimpleNamespace(is_closed=False, close=AsyncMock())
        consumer._queue = mock_queue
        consumer._connection = mock_conn
        consumer._consumer_tag = "tag-123"
        consumer._channel = SimpleNamespace()
        consumer._exchange = SimpleNamespace()

        await consumer.stop()

        mock_queue.cancel.assert_awaited_once_with("tag-123")
        mock_conn.close.assert_awaited_once()
        assert consumer._consumer_tag is None
        assert consumer._queue is None
        assert consumer._connection is None
        assert consumer.healthy is False
        assert consumer._stopped.is_set()

    async def test_stop_skips_if_no_queue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        mock_conn = SimpleNamespace(is_closed=False, close=AsyncMock())
        consumer._connection = mock_conn

        await consumer.stop()
        mock_conn.close.assert_awaited_once()

    async def test_stop_skips_if_connection_already_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        mock_conn = SimpleNamespace(is_closed=True, close=AsyncMock())
        consumer._connection = mock_conn

        await consumer.stop()
        mock_conn.close.assert_not_called()
        assert consumer._connection is None

    async def test_bind_routing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        mock_queue = SimpleNamespace(bind=AsyncMock())
        mock_exchange = _make_mock_exchange()
        consumer._queue = mock_queue
        consumer._exchange = mock_exchange

        await consumer.bind_routing_key("device.42")
        mock_queue.bind.assert_awaited_once_with(mock_exchange, routing_key="device.42")

    async def test_bind_routing_key_not_started(self) -> None:
        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        with pytest.raises(RuntimeError, match="not started"):
            await consumer.bind_routing_key("device.42")

    async def test_unbind_routing_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        mock_queue = SimpleNamespace(unbind=AsyncMock())
        mock_exchange = _make_mock_exchange()
        consumer._queue = mock_queue
        consumer._exchange = mock_exchange

        await consumer.unbind_routing_key("device.42")
        mock_queue.unbind.assert_awaited_once_with(mock_exchange, routing_key="device.42")

    async def test_unbind_routing_key_not_started(self) -> None:
        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        with pytest.raises(RuntimeError, match="not started"):
            await consumer.unbind_routing_key("device.42")

    async def test_healthy_returns_false_when_not_connected(self) -> None:
        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        assert not consumer.healthy

    async def test_healthy_returns_false_when_connection_closed(self) -> None:
        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        consumer._connection = SimpleNamespace(is_closed=True)
        assert not consumer.healthy

    async def test_healthy_returns_true_when_connected(self) -> None:
        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        consumer._connection = SimpleNamespace(is_closed=False)
        assert consumer.healthy

    def test_exchange_type_valid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)
        config = _make_consumer_config(exchange_type="fanout")
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        result = consumer._exchange_type()
        assert result.value == "fanout"

    def test_exchange_type_invalid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)
        config = _make_consumer_config(exchange_type="bogus")
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        with pytest.raises(ValueError, match="Unsupported"):
            consumer._exchange_type()

    async def test_start_raises_when_aio_pika_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", None)
        config = _make_consumer_config()
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        with pytest.raises(RuntimeError, match="aio-pika is required"):
            await consumer.start()

    async def test_on_message_calls_handler(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config()
        handler = AsyncMock()
        consumer = RabbitMQConsumer(config=config, handler=handler)

        body = json.dumps({"event_type": "test", "data": 42}).encode()
        message = MagicMock()
        message.body = body
        message.process.return_value = AsyncMock()
        message.process.return_value.__aenter__ = AsyncMock(return_value=None)
        message.process.return_value.__aexit__ = AsyncMock(return_value=False)

        await consumer._on_message(message)

        handler.assert_awaited_once_with({"event_type": "test", "data": 42})

    async def test_on_message_requeues_on_error_when_configured(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config(requeue_on_error=True)
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        consumer = RabbitMQConsumer(config=config, handler=handler)

        body = json.dumps({"event_type": "test"}).encode()
        message = MagicMock()
        message.body = body
        message.process.return_value = AsyncMock()
        message.process.return_value.__aenter__ = AsyncMock(return_value=None)
        message.process.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="boom"):
            await consumer._on_message(message)

        message.process.assert_called_once_with(requeue=True)

    async def test_on_message_does_not_requeue_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)

        config = _make_consumer_config(requeue_on_error=False)
        handler = AsyncMock(side_effect=RuntimeError("boom"))
        consumer = RabbitMQConsumer(config=config, handler=handler)

        body = json.dumps({"event_type": "test"}).encode()
        message = MagicMock()
        message.body = body
        message.process.return_value = AsyncMock()
        message.process.return_value.__aenter__ = AsyncMock(return_value=None)
        message.process.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="boom"):
            await consumer._on_message(message)

        message.process.assert_called_once_with(requeue=False)

    async def test_start_binds_multiple_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import app.infra.messaging.consumer as consumer_module

        mock_exchange = _make_mock_exchange()
        mock_queue = _make_mock_queue()

        async def fake_connect(url: str) -> SimpleNamespace:
            channel = SimpleNamespace(
                declare_exchange=AsyncMock(return_value=mock_exchange),
                declare_queue=AsyncMock(return_value=mock_queue),
                set_qos=AsyncMock(),
            )
            return SimpleNamespace(
                channel=AsyncMock(return_value=channel),
                is_closed=False,
                close=AsyncMock(),
            )

        monkeypatch.setattr(consumer_module, "aio_pika", _FakeAioPika)
        monkeypatch.setattr(_FakeAioPika, "connect_robust", fake_connect)

        config = _make_consumer_config(binding_keys=("device.#", "profile.#"))
        consumer = RabbitMQConsumer(config=config, handler=AsyncMock())
        await consumer.start()

        assert mock_queue.bind.await_count == 2


class TestProcessProfileStatusMessage:
    @patch("app.infra.messaging.consumer.async_session")
    @patch("app.infra.messaging.consumer.send_validation_webhook", new_callable=AsyncMock)
    async def test_successful_status_update_applied(self, mock_webhook: Any, mock_session_factory: Any) -> None:
        assignment = MagicMock()
        assignment.profile_id = 5
        assignment.device_id = 10
        assignment.status = "PENDING"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_profile_status_message(
            {
                "event_type": "profile.status.reported",
                "device_id": 10,
                "profile_id": 5,
                "status": "APPLIED",
            }
        )

        assert assignment.status == "APPLIED"
        assert assignment.applied_at is not None
        mock_db.commit.assert_awaited_once()
        mock_webhook.assert_awaited_once()

    @patch("app.infra.messaging.consumer.async_session")
    @patch("app.infra.messaging.consumer.send_validation_webhook", new_callable=AsyncMock)
    async def test_successful_status_update_pending(self, mock_webhook: Any, mock_session_factory: Any) -> None:
        assignment = MagicMock()
        assignment.profile_id = 5
        assignment.device_id = 10
        assignment.status = "APPLIED"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_profile_status_message(
            {
                "event_type": "profile.status.reported",
                "device_id": 10,
                "profile_id": 5,
                "status": "PENDING",
            }
        )

        assert assignment.status == "PENDING"
        mock_db.commit.assert_awaited_once()

    @patch("app.infra.messaging.consumer.async_session")
    async def test_assignment_not_found(self, mock_session_factory: Any) -> None:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_profile_status_message(
            {
                "event_type": "profile.status.reported",
                "device_id": 999,
                "profile_id": 5,
                "status": "APPLIED",
            }
        )

        mock_db.commit.assert_not_called()

    async def test_invalid_message_missing_profile_id(self) -> None:
        await process_profile_status_message({"event_type": "profile.status.reported", "device_id": 10})

    async def test_invalid_message_no_device_info(self) -> None:
        await process_profile_status_message({"event_type": "profile.status.reported", "profile_id": 5})

    async def test_invalid_status_value(self) -> None:
        await process_profile_status_message(
            {
                "event_type": "profile.status.reported",
                "device_id": 10,
                "profile_id": 5,
                "status": "INVALID",
            }
        )

    async def test_unknown_event_type_ignored(self) -> None:
        await process_profile_status_message({"event_type": "unknown.event"})

    @patch("app.infra.messaging.consumer.async_session")
    @patch("app.infra.messaging.consumer.send_validation_webhook", new_callable=AsyncMock)
    async def test_webhook_failure_does_not_nack(self, mock_webhook: Any, mock_session_factory: Any) -> None:
        mock_webhook.side_effect = RuntimeError("Webhook down")

        assignment = MagicMock()
        assignment.profile_id = 5
        assignment.device_id = 10
        assignment.status = "PENDING"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = assignment

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_profile_status_message(
            {
                "event_type": "profile.status.reported",
                "device_id": 10,
                "profile_id": 5,
                "status": "APPLIED",
            }
        )

        mock_db.commit.assert_awaited_once()
        mock_webhook.assert_awaited_once()
