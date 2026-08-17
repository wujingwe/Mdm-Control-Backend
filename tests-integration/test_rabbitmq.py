"""RabbitMQ integration tests.

Exercises the real AMQP stack (FastStream broker + aio_pika) against the broker
at RABBITMQ_URL. Publishing goes through the production ``RabbitMQProducer`` and
the ``tmdm.sse.messages`` topic exchange; consuming happens on ephemeral,
exclusive queues, and messages are identified by a unique per-test token so no
real device traffic is ever consumed or asserted on.

Run via ``make test-integration``, which also exercises the MariaDB suite.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncGenerator

import aio_pika
import pytest
import pytest_asyncio

from app.domains.devices.repositories import DeviceRepository
from app.domains.mobile_apps.repositories import MobileAppRepository
from app.domains.profiles.repositories import ProfileRepository
from app.domains.profiles.schemas.policy import Policy
from app.domains.smart_groups.repositories import SmartGroupRepository
from app.infra.config.settings import settings
from app.infra.messaging import reconciliation
from app.infra.messaging.broker import broker, exchange
from app.infra.messaging.producer import RabbitMQProducer
from app.infra.reconciler.reconciler import AssignmentReconciler

from helpers import create_device, create_mobile_app, create_profile, create_user

_EXCHANGE_NAME = exchange.name
_ALTERNATE_EXCHANGE = "tmdm.unroutable"

pytestmark = pytest.mark.skipif(
    not settings.rabbitmq_url,
    reason="RABBITMQ_URL is not configured (.env)",
)


async def _receive(
    queue: aio_pika.abc.AbstractQueue,
    token: str,
    *,
    timeout: float = 15.0,
) -> aio_pika.abc.AbstractIncomingMessage:
    """Consume until a message whose body contains ``token`` arrives.

    Filters out any stray messages (e.g. real unroutable traffic landing on the
    alternate exchange) so assertions only ever see our own message.
    """
    deadline = time.monotonic() + timeout
    needle = token.encode()
    while time.monotonic() < deadline:
        message = await queue.get(timeout=2, fail=False)
        if message is None:
            await asyncio.sleep(0.05)
            continue
        if needle in message.body:
            return message
        await message.ack()
    raise AssertionError(f"Timed out after {timeout:.1f}s waiting for a message containing {token!r}")


def _body(message: aio_pika.abc.AbstractIncomingMessage) -> dict:
    return json.loads(message.body)


@pytest_asyncio.fixture
async def amqp_connection() -> AsyncGenerator[aio_pika.abc.AbstractRobustConnection, None]:
    """Dedicated aio_pika connection used for declarations and consuming."""
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        yield connection
    finally:
        await connection.close()


@pytest_asyncio.fixture
async def started_broker() -> AsyncGenerator[None, None]:
    """Connect the shared FastStream broker and declare the SSE exchange."""
    await broker.start()
    try:
        await broker.declare_exchange(exchange)
        yield
    finally:
        await broker.stop()


@pytest_asyncio.fixture
async def rabbit_queue(
    amqp_connection: aio_pika.abc.AbstractRobustConnection,
) -> AsyncGenerator[tuple[str, aio_pika.abc.AbstractQueue], None]:
    """Ephemeral queue bound to ``#`` on the SSE exchange.

    Device serials double as routing keys and are a single AMQP word (hyphenated,
    no dots), so a ``<prefix>.#`` binding can never match them. Binding ``#``
    catches every routing key; ``_receive`` discards anything that isn't ours by
    matching on the unique per-test token in the body.
    """
    prefix = f"it-{uuid.uuid4().hex[:8]}"
    channel = await amqp_connection.channel()
    queue = await channel.declare_queue("", exclusive=True, auto_delete=True)
    await queue.bind(_EXCHANGE_NAME, routing_key="#")
    yield prefix, queue


async def test_exchange_is_declared(amqp_connection: aio_pika.abc.AbstractRobustConnection) -> None:
    channel = await amqp_connection.channel()
    declared = await channel.get_exchange(_EXCHANGE_NAME)
    assert declared.name == _EXCHANGE_NAME


async def test_topic_exchange_routes_wildcard_bindings(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
) -> None:
    prefix, queue = rabbit_queue
    await broker.publish(
        {"token": f"{prefix}-one"}, routing_key=f"{prefix}.a.b", exchange=exchange, content_type="application/json"
    )
    await broker.publish(
        {"token": f"{prefix}-two"}, routing_key=f"{prefix}.a", exchange=exchange, content_type="application/json"
    )

    first = await _receive(queue, f"{prefix}-one")
    second = await _receive(queue, f"{prefix}-two")
    assert first.routing_key == f"{prefix}.a.b"
    assert second.routing_key == f"{prefix}.a"
    await first.ack()
    await second.ack()


async def test_alternate_exchange_receives_unroutable_messages(
    started_broker: None,
    amqp_connection: aio_pika.abc.AbstractRobustConnection,
) -> None:
    channel = await amqp_connection.channel()
    alternate = await channel.declare_queue("", exclusive=True, auto_delete=True)
    await alternate.bind(_ALTERNATE_EXCHANGE, routing_key="#")

    token = f"alt-{uuid.uuid4().hex}"
    await broker.publish(
        {"token": token},
        routing_key=f"it-{uuid.uuid4().hex[:8]}.no-binding",
        exchange=exchange,
        content_type="application/json",
    )

    message = await _receive(alternate, token)
    assert _body(message) == {"token": token}
    await message.ack()


async def test_profile_push_roundtrip(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    message_id = await RabbitMQProducer.publish_profile_push(
        serial_number=serial,
        profile_id=42,
        profile_config=Policy(screenCaptureDisabled=True),
        profile_version=3,
        assignment_id=7,
    )

    message = await _receive(queue, '"kind":"profile.push"')
    body = _body(message)
    assert message.routing_key == serial
    assert message.message_id == message_id
    assert message.correlation_id == "42"
    assert body["serial_number"] == serial
    assert body["profile_id"] == 42
    assert body["profile_version"] == 3
    assert body["assignment_id"] == 7
    assert body["profile_config"]["screenCaptureDisabled"] is True
    await message.ack()


async def test_profile_revoke_roundtrip(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    message_id = await RabbitMQProducer.publish_profile_revoke(
        serial_number=serial,
        profile_id=42,
        profile_version=3,
        assignment_id=7,
    )

    message = await _receive(queue, '"kind":"profile.revoke"')
    body = _body(message)
    assert message.routing_key == serial
    assert message.message_id == message_id
    assert message.correlation_id == "42"
    assert body == {
        "kind": "profile.revoke",
        "serial_number": serial,
        "profile_id": 42,
        "profile_version": 3,
        "assignment_id": 7,
    }
    await message.ack()


async def test_mobile_app_push_roundtrip(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    message_id = await RabbitMQProducer.publish_mobile_app_push(
        serial_number=serial,
        mobile_app_id=99,
        package_name="com.example.app",
        package_version="1.0.0",
        app_version=2,
        assignment_id=7,
    )

    message = await _receive(queue, '"kind":"mobile_app.push"')
    body = _body(message)
    assert message.routing_key == serial
    assert message.message_id == message_id
    assert message.correlation_id == "99"
    assert body["mobile_app_id"] == 99
    assert body["package_name"] == "com.example.app"
    assert body["package_version"] == "1.0.0"
    assert body["app_version"] == 2
    await message.ack()


async def test_mobile_app_revoke_roundtrip(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    message_id = await RabbitMQProducer.publish_mobile_app_revoke(
        serial_number=serial,
        mobile_app_id=99,
        package_name="com.example.app",
        app_version=2,
        assignment_id=7,
    )

    message = await _receive(queue, '"kind":"mobile_app.revoke"')
    body = _body(message)
    assert message.routing_key == serial
    assert message.message_id == message_id
    assert message.correlation_id == "99"
    assert body["mobile_app_id"] == 99
    assert body["package_name"] == "com.example.app"
    assert body["app_version"] == 2
    await message.ack()


async def test_device_command_roundtrip(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    message_id = await RabbitMQProducer.publish_device_command(
        serial_number=serial,
        command_id=11,
        command_type="LOCK",
        parameters={"reason": "lost"},
    )

    message = await _receive(queue, '"kind":"device.command"')
    body = _body(message)
    assert message.routing_key == serial
    assert message.message_id == message_id
    assert message.correlation_id == "11"
    assert body == {
        "kind": "device.command",
        "serial_number": serial,
        "command_id": 11,
        "command_type": "LOCK",
        "parameters": {"reason": "lost"},
    }
    await message.ack()


async def test_request_recalculation_delivers_to_queue(
    started_broker: None,
    amqp_connection: aio_pika.abc.AbstractRobustConnection,
) -> None:
    queue_name = reconciliation._profile_queue.name
    channel = await amqp_connection.channel()
    queue = await channel.declare_queue(queue_name, auto_delete=True)

    await reconciliation.request_recalculation(
        reconciliation.RecalculationKind.PROFILE,
        entity_id=99,
        force_push=True,
    )

    message = await _receive(queue, '"entity_id"')
    assert _body(message) == {"entity_id": 99, "force_push": True}
    await message.ack()


async def test_recalculate_profile_publishes_push_via_reconciler(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
    db_session,
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    user = await create_user(db_session)
    await create_device(db_session, serial_number=serial)
    profile = await create_profile(db_session, created_by=user.id)
    await db_session.commit()
    await db_session.refresh(profile)

    reconciler = AssignmentReconciler(
        ProfileRepository(db_session),
        MobileAppRepository(db_session),
        DeviceRepository(db_session),
        SmartGroupRepository(db_session),
        RabbitMQProducer,
    )
    await reconciler.recalculate_profile(profile.id)

    message = await _receive(queue, serial)
    body = _body(message)
    assert message.routing_key == serial
    assert message.correlation_id == str(profile.id)
    assert body["kind"] == "profile.push"
    assert body["serial_number"] == serial
    assert body["profile_id"] == profile.id
    assert body["profile_version"] == profile.version
    assert body["assignment_id"] > 0
    assert body["profile_config"]["screenCaptureDisabled"] is True
    await message.ack()


async def test_recalculate_mobile_app_publishes_push_via_reconciler(
    started_broker: None,
    rabbit_queue: tuple[str, aio_pika.abc.AbstractQueue],
    db_session,
) -> None:
    prefix, queue = rabbit_queue
    serial = f"{prefix}-SN001"
    user = await create_user(db_session)
    await create_device(db_session, serial_number=serial)
    app = await create_mobile_app(db_session, created_by=user.id, package_name="com.example.integration")
    await db_session.commit()
    await db_session.refresh(app)

    reconciler = AssignmentReconciler(
        ProfileRepository(db_session),
        MobileAppRepository(db_session),
        DeviceRepository(db_session),
        SmartGroupRepository(db_session),
        RabbitMQProducer,
    )
    await reconciler.recalculate_mobile_app(app.id)

    message = await _receive(queue, serial)
    body = _body(message)
    assert message.routing_key == serial
    assert message.correlation_id == str(app.id)
    assert body["kind"] == "mobile_app.push"
    assert body["serial_number"] == serial
    assert body["mobile_app_id"] == app.id
    assert body["package_name"] == "com.example.integration"
    assert body["package_version"] == app.package_version
    assert body["app_version"] == app.version
    assert body["assignment_id"] > 0
    await message.ack()
