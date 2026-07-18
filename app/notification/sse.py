import logging

import httpx
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential

from app.config.settings import settings

logger = logging.getLogger(__name__)


async def notify_sse_server(
    device_serial: str,
    device_name: str | None = None,
    profile_id: int | None = None,
    profile_name: str | None = None,
    profile_config: dict | None = None,
) -> None:
    payload = {
        "device_serial_number": device_serial,
        "device_name": device_name,
        "profile": {
            "id": profile_id,
            "name": profile_name,
            "config": profile_config,
        },
    }
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=False,
    ):
        with attempt:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    settings.sse_server_url,
                    json=payload,
                    timeout=10.0,
                )
                resp.raise_for_status()
                logger.info(
                    "SSE server notified for device %s (status %d)",
                    device_serial,
                    resp.status_code,
                )
