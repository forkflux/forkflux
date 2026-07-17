from typing import Any, Literal


class BaseValidationError(Exception):
    code: str
    msg: str

    def __init__(
        self,
        field_name: str,
        value: Any = None,
        loc: Literal["body", "query", "header", "path"] = "body",
        detail: str | None = None,
    ):
        self.field_name = field_name
        self.value = value
        self.loc = loc
        if detail is not None:
            self.msg = f"{self.msg.rstrip('.')}: {detail}"
