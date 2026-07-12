from datetime import datetime
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    permissions: frozenset[str]
    created_at: datetime
    last_login: datetime | None = None

    model_config = {"from_attributes": True}
