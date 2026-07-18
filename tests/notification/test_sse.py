from typing import Any

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.notification.sse import notify_sse_server


class TestNotificationSSE:
    @pytest.mark.asyncio
    @patch("app.notification.sse.httpx.AsyncClient")
    async def test_notify_sse_server_success(self, mock_client_cls: Any) -> None:
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.status_code = 200
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await notify_sse_server(
            device_serial="SER001",
            device_name="Test Device",
            profile_id=1,
            profile_name="Test Profile",
            profile_config={"key": "value"},
        )
        mock_client.post.assert_called_once()
