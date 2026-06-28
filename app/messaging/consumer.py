import json
import asyncio
import logging
from sqlalchemy import select
from aiokafka import AIOKafkaConsumer
from app.config.settings import settings
from app.database import async_session
from app.models.device import Device
from app.models.policy import Policy
from app.notification.webhook import send_validation_webhook

logger = logging.getLogger(__name__)


async def process_message(data: dict) -> None:
    device_serial = data.get("device_serial_number")
    policy_id = data.get("policy_id")

    if not device_serial or not policy_id:
        logger.warning(f"Invalid message: {data}")
        return

    async with async_session() as db:
        device_stmt = select(Device).where(Device.serial_number == device_serial)
        device_result = await db.execute(device_stmt)
        device = device_result.scalar_one_or_none()

        if not device:
            logger.warning(f"Device {device_serial} not found, skipping")
            return

        policy_stmt = select(Policy).where(Policy.id == policy_id)
        policy_result = await db.execute(policy_stmt)
        policy = policy_result.scalar_one_or_none()

        if not policy:
            logger.warning(f"Policy {policy_id} not found, skipping")
            return

        if policy not in device.policies:
            device.policies.append(policy)
        device.connection_status = "configured"
        await db.commit()

    logger.info(f"Device {device_serial} updated with policy {policy_id}")

    from app.notification.sse import notify_sse_server
    await notify_sse_server(
        device_serial=device_serial,
        device_name=data.get("device_name"),
        policy_id=policy_id,
        policy_name=data.get("policy_name"),
        policy_config=data.get("policy_config"),
    )

    await send_validation_webhook(device_serial)


async def consume_policy_assignments() -> None:
    # noinspection PyBroadException
    try:
        consumer = AIOKafkaConsumer(
            settings.kafka_topic,
            bootstrap_servers=settings.kafka_bootstrap_servers,
            group_id=settings.kafka_group_id,
            value_deserializer=lambda v: json.loads(v.decode()),
            auto_offset_reset="earliest",
            enable_auto_commit=False,
        )
        await consumer.start()
        logger.info(f"Kafka consumer listening on topic '{settings.kafka_topic}'")
    except Exception:  # noqa: BLE001 — Kafka may raise various errors; consumer is optional
        logger.warning("Kafka consumer unavailable, skipping")
        return

    try:
        async for msg in consumer:
            try:
                await process_message(msg.value)
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                continue
            await consumer.commit()
    except asyncio.CancelledError:
        logger.info("Kafka consumer shutting down")
        raise
    finally:
        # noinspection PyBroadException
        try:
            await consumer.stop()
        except Exception:  # noqa: BLE001 — ignore consumer stop errors during shutdown
            pass
