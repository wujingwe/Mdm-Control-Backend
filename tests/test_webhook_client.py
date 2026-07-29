from unittest.mock import patch, AsyncMock

import httpx
import pytest

from app.webhook_client import revalidate, _get_client


class TestWebhookClient:
    async def test_revalidate_no_secret(self) -> None:
        with patch("app.webhook_client.settings") as mock:
            mock.revalidation_secret = ""
            mock.webhook_url = "http://example.com"
            await revalidate(["test"])

    async def test_revalidate_no_url(self) -> None:
        with patch("app.webhook_client.settings") as mock:
            mock.revalidation_secret = "secret"
            mock.webhook_url = ""
            await revalidate(["test"])

    async def test_revalidate_success(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = AsyncMock()
        mock_resp.is_success = True
        mock_client.post.return_value = mock_resp
        with (
            patch("app.webhook_client.settings") as mock_settings,
            patch("app.webhook_client._get_client", return_value=mock_client),
        ):
            mock_settings.revalidation_secret = "s3cret"
            mock_settings.webhook_url = "http://localhost:3000/revalidate"
            await revalidate(["profiles"])

    async def test_revalidate_http_error(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_resp = AsyncMock()
        mock_resp.is_success = False
        mock_resp.status_code = 500
        mock_resp.text = "error"
        mock_client.post.return_value = mock_resp
        with (
            patch("app.webhook_client.settings") as mock_settings,
            patch("app.webhook_client._get_client", return_value=mock_client),
        ):
            mock_settings.revalidation_secret = "s3cret"
            mock_settings.webhook_url = "http://localhost:3000/revalidate"
            await revalidate(["profiles"])

    async def test_revalidate_request_error(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.RequestError("Connection refused")
        with (
            patch("app.webhook_client.settings") as mock_settings,
            patch("app.webhook_client._get_client", return_value=mock_client),
        ):
            mock_settings.revalidation_secret = "s3cret"
            mock_settings.webhook_url = "http://localhost:3000/revalidate"
            await revalidate(["profiles"])

    async def test_get_client_cached(self) -> None:
        _get_client.cache_clear()
        c1 = _get_client()
        c2 = _get_client()
        assert c1 is c2
