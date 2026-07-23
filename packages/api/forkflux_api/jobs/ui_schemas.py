from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from forkflux_api.jobs.constants import JobPriorityEnum, JobStatusEnum


class JobUiListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_job_id: int | None
    parent_job_summary: str | None
    summary: str
    status: JobStatusEnum
    priority: JobPriorityEnum
    source_agent_label: str
    assignee_agent_label: str | None
    target_role_label: str
    created_at: datetime


class JobUiListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[JobUiListItem]
    total: int
    limit: int
    offset: int


class JobStatusCountsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    counts: dict[JobStatusEnum, int]


class JobArtifactUiItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    artifact_type: str
    artifact_uri: str
    artifact_checksum: str | None
    metadata_json: dict[str, Any]
    created_at: datetime


class JobEventUiItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str
    current_status: JobStatusEnum
    actor_agent_label: str | None
    payload_json: dict[str, Any]
    created_at: datetime


class JobUiDetailItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_job_id: int | None
    parent_job_summary: str | None
    summary: str
    context_payload: dict[str, Any]
    status: JobStatusEnum
    priority: JobPriorityEnum

    source_agent_label: str
    assignee_agent_label: str | None
    target_role_label: str

    constraints: list[str]
    artifacts: list[JobArtifactUiItem]
    events: list[JobEventUiItem]
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


class UnblockJobRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    unblock_reason: str


class UnblockJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    previous_status: JobStatusEnum
    new_status: JobStatusEnum
    unblock_reason: str
