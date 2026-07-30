import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.lifecycle import Lifecycle


class TestLifecycle:
    async def test_start_stop_without_consumer(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.lifecycle.settings") as mock_settings:
            mock_settings.rabbitmq_consumer_enabled = False
            await lifecycle.start()
        await lifecycle.stop()

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    async def test_start_rabbitmq_failure(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.lifecycle.settings") as mock_settings:
            mock_settings.rabbitmq_consumer_enabled = False
            with patch(
                "app.infra.messaging.producer.rabbitmq_producer.start", side_effect=RuntimeError("Not available")
            ):
                await lifecycle.start()
        await lifecycle.stop()

    async def test_start_with_consumer(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.lifecycle.settings") as mock_settings:
            mock_settings.rabbitmq_consumer_enabled = True
            with patch("app.infra.messaging.consumer.rabbitmq_consumer") as mock_c:
                mock_c.run_until_stopped = AsyncMock()
                with patch("app.infra.messaging.producer.rabbitmq_producer"):
                    await lifecycle.start()
        await asyncio.sleep(0)
        assert lifecycle._consumer_task is not None
        mock_c.run_until_stopped.assert_awaited_once()
        lifecycle._consumer_task.cancel()
        await lifecycle.stop()

    async def test_start_with_consumer_failure(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.lifecycle.settings") as mock_settings:
            mock_settings.rabbitmq_consumer_enabled = True
            with patch("app.infra.messaging.consumer.rabbitmq_consumer") as mock_c:
                mock_c.run_until_stopped = AsyncMock(side_effect=RuntimeError("consumer fail"))
                with patch("app.infra.messaging.producer.rabbitmq_producer"):
                    await lifecycle.start()
        await asyncio.sleep(0)
        assert lifecycle._consumer_task is not None
        mock_c.run_until_stopped.assert_awaited_once()
        await lifecycle.stop()

    async def test_consumer_task_cancelled(self) -> None:
        never = asyncio.get_event_loop().create_future()
        lifecycle = Lifecycle()
        with patch("app.lifecycle.settings") as mock_settings:
            mock_settings.rabbitmq_consumer_enabled = True
            with patch("app.infra.messaging.consumer.rabbitmq_consumer") as mock_c:
                mock_c.run_until_stopped = AsyncMock(side_effect=lambda: never)
                with patch("app.infra.messaging.producer.rabbitmq_producer"):
                    await lifecycle.start()
        await asyncio.sleep(0)
        assert lifecycle._consumer_task is not None
        await lifecycle.stop()

    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    async def test_stop_consumer_without_task(self) -> None:
        lifecycle = Lifecycle()
        await lifecycle._stop_consumer()

    async def test_stop_rabbitmq_failure(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.infra.messaging.producer.rabbitmq_producer.stop", side_effect=RuntimeError("stop fail")):
            await lifecycle.stop()

    async def test_full_start_stop_consumer_enabled(self) -> None:
        lifecycle = Lifecycle()
        with patch("app.lifecycle.settings") as mock_settings:
            mock_settings.rabbitmq_consumer_enabled = True
            with patch("app.infra.messaging.consumer.rabbitmq_consumer") as mock_c:
                mock_c.run_until_stopped = AsyncMock()
                with patch("app.infra.messaging.producer.rabbitmq_producer"):
                    await lifecycle.start()
        await asyncio.sleep(0)
        assert lifecycle._consumer_task is not None
        await lifecycle.stop()
        assert lifecycle._consumer_task.done()
