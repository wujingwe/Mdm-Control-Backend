"""Thin domain service exposing the stale-assignment sweep to the API layer."""

from app.infra.reconciler.reconciler import (
    DEFAULT_BACKOFF_SECONDS,
    AssignmentReconciler,
    SweepResult,
)


class SweepService:
    """Re-send assignment messages that were never acknowledged by devices."""

    def __init__(self, reconciler: AssignmentReconciler) -> None:
        self.reconciler = reconciler

    async def sweep_stale_assignments(
        self,
        *,
        limit: int = 500,
        backoff_seconds: tuple[int, ...] = DEFAULT_BACKOFF_SECONDS,
    ) -> SweepResult:
        return await self.reconciler.sweep_stale_assignments(
            limit=limit,
            backoff_seconds=backoff_seconds,
        )
