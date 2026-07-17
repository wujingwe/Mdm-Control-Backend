import logging

import httpx
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential
from app.config.settings import settings

logger = logging.getLogger(__name__)


async def send_validation_webhook(device_serial_number: str) -> None:
    payload = {"tag": ["devices", f"device:{device_serial_number}"]}
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=False,
    ):
        with attempt:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    settings.webhook_url,
                    json=payload,
                    timeout=10.0,
                )
                resp.raise_for_status()
                logger.info(
                    "Webhook sent for device %s (status %d)",
                    device_serial_number,
                    resp.status_code,
                )
