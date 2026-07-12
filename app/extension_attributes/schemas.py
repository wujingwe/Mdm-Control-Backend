from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class DataType(str, Enum):
    string = "string"
    integer = "integer"
    date = "date"


class InputType(str, Enum):
    text_field = "Text field"
    popup_menu = "Pop-up menu"


class ExtensionAttributeCreate(BaseModel):
    name: str
    description: str | None = None
    data_type: DataType
    input_type: InputType
    popup_choices: list[str] | None = None
    created_by: int = 1


class ExtensionAttributeUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    data_type: DataType | None = None
    input_type: InputType | None = None
    popup_choices: list[str] | None = None


class ExtensionAttributeResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    data_type: DataType
    input_type: InputType
    popup_choices: list[str] | None = None
    created_at: datetime
    created_by: int
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}
