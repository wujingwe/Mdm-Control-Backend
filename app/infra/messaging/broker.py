from __future__ import annotations

import logging

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange

from app.infra.config.settings import settings

logger = logging.getLogger(__name__)

broker = RabbitBroker(settings.rabbitmq_url)

exchange = RabbitExchange(
    "tmdm.sse.messages",
    type=ExchangeType.TOPIC,
    durable=True,
)
