from fastapi import APIRouter, Depends, HTTPException, Query
from app.dependencies import get_policy_service
from app.policies.schemas import PolicyCreate, PolicyUpdate, PolicyResponse
from app.common.schemas import Message, PaginatedResponse
from app.policies.services import PolicyService
from app.webhook_client import revalidate
from app.messaging.producer import rabbitmq_producer

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("", response_model=PaginatedResponse[PolicyResponse])
async def list_policies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: PolicyService = Depends(get_policy_service),
) -> PaginatedResponse[PolicyResponse]:
    items, total = await service.list_policies(skip=skip, limit=limit)
    return PaginatedResponse(
        items=[PolicyResponse.model_validate(p) for p in items],
        total=total, skip=skip, limit=limit,
    )


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: int,
    service: PolicyService = Depends(get_policy_service),
) -> PolicyResponse:
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return PolicyResponse.model_validate(policy)


@router.post("", response_model=PolicyResponse, status_code=201)
async def create_policy(
    data: PolicyCreate,
    service: PolicyService = Depends(get_policy_service),
) -> PolicyResponse:
    settings = data.settings or {}
    policy = await service.create_policy({
        "name": data.name,
        "scope": data.scope,
        "rollout_state": "Pending",
        "target_devices": data.target_devices,
        "applied_devices": 0,
        "settings": settings,
    })
    await revalidate(["policies"])
    return PolicyResponse.model_validate(policy)


@router.put("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: int,
    data: PolicyUpdate,
    service: PolicyService = Depends(get_policy_service),
) -> PolicyResponse:
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    update: dict = {}
    if data.name is not None:
        update["name"] = data.name
    if data.scope is not None:
        update["scope"] = data.scope
    if data.settings is not None:
        update["settings"] = data.settings
    updated = await service.update_policy(policy_id, update)
    await revalidate(["policies"])
    return PolicyResponse.model_validate(updated)


@router.post("/{policy_id}/push", response_model=Message)
async def push_policy(
    policy_id: int,
    device_id: int = Query(...),
    service: PolicyService = Depends(get_policy_service),
) -> Message:
    policy = await service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    try:
        await rabbitmq_producer.publish_policy_deployment(
            device_id=device_id,
            policy_id=policy.id,
            policy_name=policy.name,
            policy_config=policy.settings or {},
        )
    except RuntimeError as err:
        raise HTTPException(status_code=503, detail="RabbitMQ producer not available") from err
    except Exception as err:
        raise HTTPException(status_code=503, detail=f"RabbitMQ publish failed: {err}") from err

    await service.update_policy(policy_id, {"rollout_state": "Pushing"})
    await revalidate(["policies"])
    return Message(detail="Policy pushed to devices")
