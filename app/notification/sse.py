import logging

import httpx
from tenacity import AsyncRetrying, stop_after_attempt, wait_exponential
from app.config.settings import settings

logger = logging.getLogger(__name__)


async def notify_sse_server(
    device_serial: str,
    device_name: str | None = None,
    policy_id: int | None = None,
    policy_name: str | None = None,
    policy_config: dict | None = None,
) -> None:
    payload = {
        "device_serial_number": device_serial,
        "device_name": device_name,
        "policy": {
            "id": policy_id,
            "name": policy_name,
            "config": policy_config,
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
                    settings.sse_server_url, json=payload, timeout=10.0,
                )
                resp.raise_for_status()
                logger.info(
                    "SSE server notified for device %s (status %d)",
                    device_serial,
                    resp.status_code,
                )


async def notify_group_policy_assignment(
    group_id: int,
    group_name: str,
    policy_id: int,
    policy_name: str,
) -> None:
    payload = {
        "group_id": group_id,
        "group_name": group_name,
        "policy": {
            "id": policy_id,
            "name": policy_name,
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
                    settings.sse_server_url, json=payload, timeout=10.0,
                )
                resp.raise_for_status()
                logger.info(
                    "SSE server notified for group %d policy %d (status %d)",
                    group_id,
                    policy_id,
                    resp.status_code,
                )
