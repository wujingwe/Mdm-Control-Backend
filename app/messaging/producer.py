import json
import logging
from aiokafka import AIOKafkaProducer
from app.config.settings import settings

logger = logging.getLogger(__name__)


class KafkaProducerService:
    def __init__(self) -> None:
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode(),
        )
        await self._producer.start()
        logger.info("Kafka producer connected")

    async def stop(self) -> None:
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer disconnected")

    async def send_event(self, topic: str, key: str, value: dict) -> None:
        if not self._producer:
            raise RuntimeError("Kafka producer not started")  # noqa: TRY003
        await self._producer.send(topic, key=key.encode(), value=value)

    @property
    def healthy(self) -> bool:
        return self._producer is not None and not self._producer._closed


kafka_producer = KafkaProducerService()
