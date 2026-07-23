from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from forkflux_api.jobs.constants import JobPriorityEnum, JobStatusEnum


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


class HandoffJobListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_job_id: int | None
    summary: str
    status: JobStatusEnum
    priority: JobPriorityEnum
    source_agent_label: str
    assignee_agent_label: str | None
    target_role_key: str
    created_at: datetime


class HandoffJobWithArtifactsItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_job_id: int | None
    summary: str
    context_payload: dict[str, Any]
    status: JobStatusEnum
    priority: JobPriorityEnum

    source_agent_label: str
    assignee_agent_label: str | None
    target_role_key: str

    constraints: list[str]
    artifacts: list[JobArtifact]
    failure_reason: str | None
    blocked_reason: str | None
    unblock_reason: str | None

    published_at: datetime
    claimed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    blocked_at: datetime | None
    unblocked_at: datetime | None
    cancelled_at: datetime | None
    expires_at: datetime | None

    created_at: datetime
    updated_at: datetime


class HandoffJobChangeStatusRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: JobStatusEnum
    failure_reason: str | None = None
    blocked_reason: str | None = None
    unblock_reason: str | None = None


class HandoffJobChangeStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    previous_status: JobStatusEnum
    new_status: JobStatusEnum


class HandoffJobClaimNextRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_role_key: str


class HandoffJobUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    context_payload: dict[str, Any] | None = None
    constraints: list[str] | None = None

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> "HandoffJobUpdateRequest":
        if self.context_payload is None and self.constraints is None:
            raise ValueError("At least one of context_payload or constraints must be provided")
        return self


class HandoffJobUpdateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    message: str
