from pydantic import BaseModel


class PolicyCreate(BaseModel):
    name: str
    scope: str
    target_devices: int = 0
    settings: dict | None = None


class PolicyUpdate(BaseModel):
    name: str | None = None
    scope: str | None = None
    settings: dict | None = None


class PolicyResponse(BaseModel):
    id: int
    name: str
    version: int
    scope: str
    rollout_state: str
    target_devices: int
    applied_devices: int
    description: str | None = None
    settings: dict | None = None

    model_config = {"from_attributes": True}
