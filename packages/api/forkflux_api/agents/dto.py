from dataclasses import dataclass


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
