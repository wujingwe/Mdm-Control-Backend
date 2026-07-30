from enum import Enum


class ExtensionDataType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    DATE = "date"


class ExtensionInputType(str, Enum):
    TEXT_FIELD = "Text field"
    POPUP_MENU = "Pop-up menu"
