from pydantic import BaseModel, ConfigDict


class ListRolesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role_key: str
    role_label: str


class GetMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    agent_label: str
    tool_family: str | None
