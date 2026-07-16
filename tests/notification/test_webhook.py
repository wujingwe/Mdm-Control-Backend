import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.notification.webhook import send_validation_webhook


class TestNotificationWebhook:
    @pytest.mark.asyncio
    @patch("app.notification.webhook.httpx.AsyncClient")
    async def test_send_validation_webhook_success(self, mock_client_cls):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await send_validation_webhook("SER001")
        mock_client.post.assert_called_once()
