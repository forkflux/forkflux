from typing import Any, Literal


class BaseValidationError(Exception):
    code: str
    msg: str

    def __init__(self, field_name: str, value: Any = None, loc: Literal["body", "query", "header"] = "body"):
        self.field_name = field_name
        self.value = value
        self.loc = loc
