from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.dependencies import get_sweep_service
from app.infra.reconciler.reconciler import SweepResult
from app.main import app


@pytest.mark.asyncio
async def test_sweep_endpoint_invokes_reconciler(client: AsyncClient) -> None:
    fake_sweep_service = AsyncMock()
    fake_sweep_service.sweep_stale_assignments = AsyncMock(return_value=SweepResult(profile_push_sent=3, gave_up=1))
    app.dependency_overrides[get_sweep_service] = lambda: fake_sweep_service
    try:
        response = await client.post("/api/v1/assignments/sweep")
        assert response.status_code == 200
        body: dict[str, Any] = response.json()
        assert body["profile_push_sent"] == 3
        assert body["gave_up"] == 1
        fake_sweep_service.sweep_stale_assignments.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_sweep_service, None)
