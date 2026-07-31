from unittest.mock import AsyncMock, patch

import pytest

from app.lifecycle import Lifecycle


class TestLifecycle:
    async def test_start_stop(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.lifecycle.broker.start", AsyncMock()), patch("app.lifecycle.broker.stop", AsyncMock()):
            await lifecycle.start()
        await lifecycle.stop()

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    async def test_start_rabbitmq_failure(self) -> None:
        lifecycle = Lifecycle()
        with (
            patch("app.lifecycle.broker.start", AsyncMock(side_effect=RuntimeError("Not available"))),
            patch("app.lifecycle.broker.stop", AsyncMock()),
        ):
            await lifecycle.start()
        await lifecycle.stop()

    async def test_stop_rabbitmq_failure(self) -> None:
        lifecycle = Lifecycle()
        with (
            patch("app.lifecycle.broker.start", AsyncMock()),
            patch("app.lifecycle.broker.stop", AsyncMock(side_effect=RuntimeError("stop fail"))),
        ):
            await lifecycle.start()
            await lifecycle.stop()
