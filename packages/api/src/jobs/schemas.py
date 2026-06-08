from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from src.jobs.constants import JobPriorityEnum, JobStatusEnum


class JobArtifact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    uri: str
    checksum: str | None
    metadata_json: dict[str, Any]


class HandoffJobCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parent_job_id: int | None
    summary: str
    context_payload: dict[str, Any]
    target_role_key: str
    constraints: list[str]
    artifacts: list[JobArtifact]
    priority: JobPriorityEnum


class HandoffJobCreateResponse(BaseModel):
    job_id: int


class HandoffJobFilterParams(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    limit: int = Field(50, ge=50, le=200)
    status: JobStatusEnum | None = None
    target_role_key: str | None = None


class HandoffJobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    summary: str
    status: JobStatusEnum
    priority: JobPriorityEnum
    source_agent_label: str
    assignee_agent_label: str | None
    target_role_key: str
    created_at: datetime
