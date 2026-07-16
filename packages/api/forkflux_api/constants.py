from enum import Enum


class CLIScopeEnum(str, Enum):
    local = "local"
    project = "project"
    user = "user"
