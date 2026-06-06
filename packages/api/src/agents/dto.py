from dataclasses import dataclass


@dataclass(slots=True)
class TargetRoleCreate:
    role_key: str
    role_label: str


@dataclass(slots=True)
class AgentIdentityCreate:
    agent_label: str
    role_id: int
    tool_family: str | None


@dataclass(slots=True)
class AgentApiTokenCreate:
    agent_id: int
