from unittest.mock import AsyncMock, MagicMock

import pytest

from app.infra.messaging import reconciliation
from app.infra.messaging.reconciliation import (
    ReconciliationRequest,
    RecalculationKind,
    request_recalculation,
)
from app.infra.messaging.reconciliation_worker import register_handlers


class TestRequestRecalculation:
    async def test_profile_routes_to_profile_queue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await request_recalculation(RecalculationKind.PROFILE, 42, force_push=True)

        mock_publish.assert_awaited_once_with(
            {"entity_id": 42, "force_push": True},
            queue=reconciliation._profile_queue,
        )

    async def test_mobile_app_routes_to_mobile_app_queue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_publish = AsyncMock()
        monkeypatch.setattr("app.infra.messaging.reconciliation.broker.publish", mock_publish)

        await request_recalculation(RecalculationKind.MOBILE_APP, 7)

        mock_publish.assert_awaited_once_with(
            {"entity_id": 7, "force_push": False},
            queue=reconciliation._mobile_app_queue,
        )


def _register_with_fake(monkeypatch, *, reconciler_factory=None):
    """Register handlers with a mock broker and fake session.

    Returns (subscriber_mock, profile_handler, mobile_app_handler).
    """
    mock_broker_subscriber = MagicMock()
    monkeypatch.setattr(
        "app.infra.messaging.reconciliation_worker.broker.subscriber",
        mock_broker_subscriber,
    )

    if reconciler_factory is not None:
        monkeypatch.setattr(
            "app.infra.messaging.reconciliation_worker.AssignmentReconciler",
            reconciler_factory,
        )

    mock_session_factory = MagicMock()
    register_handlers(mock_session_factory)

    # broker.subscriber(queue) returns a decorator, decorator(func) returns the handler.
    # call_args_list[0] = broker.subscriber(_profile_queue)
    # call_args_list[1] = decorator(profile_handler_func)
    profile_handler = mock_broker_subscriber.return_value.call_args_list[0][0][0]
    mobile_app_handler = mock_broker_subscriber.return_value.call_args_list[1][0][0]
    return mock_broker_subscriber, profile_handler, mobile_app_handler


class TestReconciliationSubscribers:
    async def test_profile_subscriber_calls_reconciler(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_reconciler = MagicMock()
        mock_reconciler.recalculate_profile = AsyncMock()
        _, profile_handler, _ = _register_with_fake(
            monkeypatch,
            reconciler_factory=MagicMock(return_value=mock_reconciler),
        )

        await profile_handler(ReconciliationRequest(entity_id=42, force_push=True))

        mock_reconciler.recalculate_profile.assert_awaited_once_with(42, force_push=True)

    async def test_mobile_app_subscriber_calls_reconciler(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_reconciler = MagicMock()
        mock_reconciler.recalculate_mobile_app = AsyncMock()
        _, _, mobile_app_handler = _register_with_fake(
            monkeypatch,
            reconciler_factory=MagicMock(return_value=mock_reconciler),
        )

        await mobile_app_handler(ReconciliationRequest(entity_id=7))

        mock_reconciler.recalculate_mobile_app.assert_awaited_once_with(7, force_push=False)

    async def test_profile_handlerRegistersOnCorrectQueue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_broker_subscriber, _, _ = _register_with_fake(monkeypatch)

        mock_broker_subscriber.assert_any_call(reconciliation._profile_queue)

    async def test_mobile_app_handlerRegistersOnCorrectQueue(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_broker_subscriber, _, _ = _register_with_fake(monkeypatch)

        mock_broker_subscriber.assert_any_call(reconciliation._mobile_app_queue)
