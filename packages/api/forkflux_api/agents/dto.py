from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class TargetRoleCreate:
    role_key: str
    role_label: str


@dataclass(slots=True)
class AgentIdentityCreate:
    agent_label: str
    tool_family: str | None


@dataclass(slots=True)
class AgentApiTokenCreate:
    agent_id: int


@dataclass(slots=True)
class AgentIdentityRoleAssign:
    agent_identity_id: int
    target_role_id: int


@dataclass(slots=True)
class RoleSummary:
    role_key: str
    role_label: str


@dataclass(slots=True)
class AgentIdentityWithRoles:
    id: int
    agent_label: str
    tool_family: str | None
    created_at: datetime
    roles: list[RoleSummary]


@dataclass(slots=True)
class AgentRegistration:
    agent_label: str
    tool_family: str | None
    target_role_ids: list[int]


@dataclass(slots=True)
class AgentRegistrationResult:
    agent_id: int
    agent_label: str
    tool_family: str | None
    target_role_ids: list[int]
    api_token: str
