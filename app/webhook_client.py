import logging
from functools import lru_cache

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=5.0)


async def revalidate(tags: list[str]) -> None:
    secret = settings.revalidation_secret
    if not secret:
        logger.warning("REVALIDATION_SECRET not set, skipping webhook")
        return

    url = settings.webhook_url
    if not url:
        logger.warning("WEBHOOK_URL not set, skipping webhook")
        return

    try:
        client = _get_client()
        resp = await client.post(
            url,
            json={"tags": tags},
            headers={"x-revalidation-secret": secret},
        )
        if resp.is_success:
            logger.info("Cache revalidated tags=%s", tags)
        else:
            logger.warning(
                "Revalidation webhook returned %s: %s",
                resp.status_code,
                resp.text,
            )
    except httpx.RequestError as exc:
        logger.warning("Revalidation webhook request failed: %s", exc)
    except Exception as exc:  # noqa: BLE001 — webhook failure shouldn't crash the request
        logger.warning("Revalidation webhook error: %s", exc)
