from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forkflux_api.jobs.constants import JobPriorityEnum, JobStatusEnum


class JobArtifact(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    uri: str
    checksum: str | None
    metadata_json: dict[str, Any]


class HandoffJobReopenContextResponse(BaseModel):
    """Focused reopen context — returns only the diff/rejection metadata,
    not the full original ``context_payload``.

    This is the context-window-management feature: CLI agents with limited
    context windows get the rejection reason, retry count, and constraints
    without parsing the entire original context blob.
    """

    model_config = ConfigDict(from_attributes=True)

    job_id: int
    original_job_id: int
    rejected_by_job_id: int
    retry_count: int
    max_retries: int
    rejection_reason: str
    summary: str
    constraints: list[Any]
    target_role_key: str


class RoutingRule(BaseModel):
    """A single conditional routing rule — a job template to be auto-created
    when the parent job transitions to COMPLETED.

    The source agent specifies ``target_role_key`` (a string). The API
    resolves it to ``target_role_id`` at validation time and stores both
    in the database. In create requests, ``target_role_id`` is absent;
    in responses, it is populated from the stored JSON.

    Note: ``target_role_key`` is a historical snapshot taken at creation
    time. If the role is renamed after the job is created, the stored key
    will not reflect the new name. The ``target_role_id`` is the
    authoritative executable reference; the key is for human readability.
    """

    model_config = ConfigDict(from_attributes=True)

    target_role_key: str | None = None
    target_role_id: int | None = None
    summary: str
    context_payload: dict[str, Any] = Field(default_factory=dict)
    constraints: list[str] = Field(default_factory=list)
    priority: JobPriorityEnum
    artifacts: list[JobArtifact] = Field(default_factory=list)


class HandoffJobCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parent_job_id: int | None
    summary: str
    context_payload: dict[str, Any]
    target_role_key: str
    constraints: list[str]
    artifacts: list[JobArtifact]
    priority: JobPriorityEnum
    blocked_by: list[int] = []
    routing_rules: list[RoutingRule] | None = Field(
        default=None,
        max_length=10,
        description="Optional conditional routing rules. When the job transitions to 'completed', "
        "each rule auto-creates a new 'published' job. Maximum 10 rules.",
    )


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
    retry_count: int
    max_retries: int
    routing_rules: list[RoutingRule] | None
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
    retry_count: int
    max_retries: int
    routing_rules: list[RoutingRule] | None
    artifacts: list[JobArtifact]
    failure_reason: str | None
    blocked_reason: str | None
    unblock_reason: str | None

    published_at: datetime | None
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


class HandoffJobRejectRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_job_id: int
    reason: str = Field(
        min_length=1, description="A detailed explanation of why the work is being rejected. Must be non-empty."
    )

    @model_validator(mode="after")
    def _reason_must_not_be_whitespace_only(self) -> "HandoffJobRejectRequest":
        if self.reason.strip() == "":
            raise ValueError("reason must not be empty or whitespace-only")
        return self


class HandoffJobRejectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: int
    original_job_id: int
    retry_count: int


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
