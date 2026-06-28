from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.models.device import Device
from app.models.policy import Policy
from pydantic import BaseModel

router = APIRouter(prefix="/metrics", tags=["Metrics"])


class FleetMetricsResponse(BaseModel):
    total_devices: int
    online_devices: int
    pending_policies: int


@router.get("/fleet", response_model=FleetMetricsResponse)
async def fleet_metrics(db: AsyncSession = Depends(get_db)) -> FleetMetricsResponse:
    total = await db.execute(select(func.count(Device.id)))
    total_devices = total.scalar() or 0

    online = await db.execute(
        select(func.count(Device.id)).where(Device.connection_status == "Online"),
    )
    online_devices = online.scalar() or 0

    pending = await db.execute(
        select(func.count(Policy.id)).where(Policy.rollout_state == "Pending"),
    )
    pending_policies = pending.scalar() or 0

    return FleetMetricsResponse(
        total_devices=total_devices,
        online_devices=online_devices,
        pending_policies=pending_policies,
    )
