from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import tenacity

from app.config.settings import settings
from app.notification.sse import notify_sse_server


@pytest.fixture
def mock_client() -> AsyncMock:
    with patch("app.notification.sse.httpx.AsyncClient") as m:
        client_instance = AsyncMock()
        m.return_value.__aenter__.return_value = client_instance
        yield client_instance


class TestNotifySSEServer:
    async def test_success(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
        await notify_sse_server(
            device_serial="SN001",
            device_name="MacBook",
            profile_id=1,
            profile_name="Profile A",
            profile_config={"key": "val"},
        )
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == settings.sse_server_url
        assert call_kwargs[1]["json"] == {
            "device_serial_number": "SN001",
            "device_name": "MacBook",
            "profile": {"id": 1, "name": "Profile A", "config": {"key": "val"}},
        }

    async def test_retry_then_succeed(self, mock_client: AsyncMock) -> None:
        fail = httpx.HTTPStatusError(
            "fail", request=MagicMock(), response=MagicMock(status_code=500)
        )
        mock_client.post = AsyncMock(
            side_effect=[fail, fail, MagicMock(status_code=200)]
        )
        await notify_sse_server(device_serial="SN001")
        assert mock_client.post.call_count == 3

    async def test_all_retries_fail_raises_retry_error(self, mock_client: AsyncMock) -> None:
        mock_client.post = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "fail", request=MagicMock(), response=MagicMock(status_code=500)
            )
        )
        with pytest.raises(tenacity.RetryError):
            await notify_sse_server(device_serial="SN001")
        assert mock_client.post.call_count == 3
