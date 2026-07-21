from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateRoleRequest(BaseModel):
    role_key: str = Field(min_length=1, max_length=255)
    role_label: str = Field(min_length=1, max_length=255)


class CreateAgentRequest(BaseModel):
    agent_label: str = Field(min_length=1, max_length=255)
    tool_family: str | None = Field(default=None, max_length=255)
    target_role_ids: list[int] = Field(min_length=1)


class CreateAgentResponse(BaseModel):
    agent_id: int
    agent_label: str
    tool_family: str | None
    target_role_ids: list[int]
    api_token: str


class ListRolesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role_key: str
    role_label: str
    created_at: datetime


class AgentRoleSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_key: str
    role_label: str


class ListAgentsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_label: str
    tool_family: str | None
    created_at: datetime
    roles: list[AgentRoleSummary] = []
