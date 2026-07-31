from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.messaging import reconciliation, reconciliation_worker
from app.infra.messaging.reconciliation import (
    ReconciliationRequest,
    RecalculationKind,
    request_recalculation,
)
from app.infra.messaging.reconciliation_worker import (
    _recalculate_mobile_app,
    _recalculate_profile,
    handle_mobile_app_recalculate,
    handle_profile_recalculate,
)


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


class TestReconciliationSubscribers:
    async def test_profile_subscriber_calls_profile_recalculate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_recalc = AsyncMock()
        monkeypatch.setattr(reconciliation_worker, "_recalculate_profile", mock_recalc)

        await handle_profile_recalculate(ReconciliationRequest(entity_id=42, force_push=True))

        mock_recalc.assert_awaited_once_with(42, force_push=True)

    async def test_mobile_app_subscriber_calls_mobile_app_recalculate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_recalc = AsyncMock()
        monkeypatch.setattr(reconciliation_worker, "_recalculate_mobile_app", mock_recalc)

        await handle_mobile_app_recalculate(ReconciliationRequest(entity_id=7))

        mock_recalc.assert_awaited_once_with(7, force_push=False)


class TestReconcileHandlers:
    async def test_recalculate_profile_builds_reconciler(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        mock_reconciler = MagicMock()
        mock_reconciler.recalculate_profile = AsyncMock()
        monkeypatch.setattr(
            reconciliation_worker,
            "AssignmentReconciler",
            MagicMock(return_value=mock_reconciler),
        )

        @asynccontextmanager
        async def _fake_session():
            yield db_session

        monkeypatch.setattr("app.infra.core.database.async_session", _fake_session)

        await _recalculate_profile(42, force_push=True)

        mock_reconciler.recalculate_profile.assert_awaited_once_with(42, force_push=True)

    async def test_recalculate_mobile_app_builds_reconciler(
        self, monkeypatch: pytest.MonkeyPatch, db_session: AsyncSession
    ) -> None:
        mock_reconciler = MagicMock()
        mock_reconciler.recalculate_mobile_app = AsyncMock()
        monkeypatch.setattr(
            reconciliation_worker,
            "AssignmentReconciler",
            MagicMock(return_value=mock_reconciler),
        )

        @asynccontextmanager
        async def _fake_session():
            yield db_session

        monkeypatch.setattr("app.infra.core.database.async_session", _fake_session)

        await _recalculate_mobile_app(7)

        mock_reconciler.recalculate_mobile_app.assert_awaited_once_with(7, force_push=False)
