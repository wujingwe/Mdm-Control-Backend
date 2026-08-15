from fastapi import APIRouter, Depends

from app.dependencies import get_sweep_service, require_sweep_secret
from app.domains.shared.sweep_service import SweepService
from app.infra.reconciler.reconciler import SweepResult

router = APIRouter(prefix="/assignments", tags=["Assignments"])


@router.post("/sweep", response_model=SweepResult, summary="Re-send unacknowledged assignment messages")
async def sweep_assignments(
    _secret: None = Depends(require_sweep_secret),
    sweep_service: SweepService = Depends(get_sweep_service),
) -> SweepResult:
    """Re-publish profile/app push and revoke messages that devices never acknowledged.

    Intended to be triggered periodically from a k8s CronJob.
    """
    return await sweep_service.sweep_stale_assignments()
