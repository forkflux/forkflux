from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict

from forkflux_api.jobs.constants import JobEventTypeEnum, JobListOrderEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.models import HandoffJob, JobArtifact


@dataclass(slots=True)
class HandoffJobCreate:
    parent_job_id: int | None
    summary: str
    context_payload: dict[str, Any]
    priority: JobPriorityEnum
    source_agent_id: int
    target_role_id: int
    constraints: list[str]


@dataclass(slots=True)
class HandoffJobUpdate:
    context_payload: dict[str, Any] | None = None
    constraints: list[str] | None = None


@dataclass(slots=True)
class JobArtifactCreate:
    job_id: int
    artifact_type: str
    artifact_uri: str
    artifact_checksum: str | None
    metadata_json: dict[str, Any]


@dataclass(slots=True)
class JobEventCreate:
    job_id: int
    event_type: JobEventTypeEnum
    previous_status: JobStatusEnum | None
    current_status: JobStatusEnum
    actor_agent_id: int | None
    payload_json: dict[str, Any]


@dataclass(slots=True)
class HandoffJobItem:
    job_details: HandoffJob
    target_role_key: str
    source_agent_label: str
    assignee_agent_label: str | None


class HandoffJobWithArtifacts(TypedDict):
    job: HandoffJobItem
    artifacts: list[JobArtifact]


class HandoffJobWithArtifactsAndEvents(TypedDict):
    job: HandoffJobUiDetailItem
    artifacts: list[JobArtifact]
    events: list[JobEventUiItem]


@dataclass(slots=True)
class HandoffJobFilterParams:
    limit: int
    statuses: list[JobStatusEnum]
    target_role_ids: list[int]
    order: list[JobListOrderEnum]
    offset: int = 0


@dataclass(slots=True)
class HandoffJobStats:
    window_hours: int
    stuck_minutes: int
    total_jobs: int
    all_time_status_counts: dict[JobStatusEnum, int]
    queue_status_counts: dict[JobStatusEnum, int]
    terminal_status_counts: dict[JobStatusEnum, int]
    completion_rate: float
    failure_rate: float
    blocked_rate: float
    active_agents: int
    stuck_jobs: int
    total_handoffs: int
    estimated_time_saved_minutes: int
    waiting_jobs_by_role: list[tuple[str, int]]
    p50_time_to_claim_minutes: float | None
    p90_time_to_claim_minutes: float | None
    p50_time_to_resolution_minutes: float | None
    p90_time_to_resolution_minutes: float | None


@dataclass(slots=True)
class HandoffJobRawStats:
    window_hours: int
    stuck_minutes: int
    total_jobs: int
    all_time_status_counts: dict[JobStatusEnum, int]
    status_counts: dict[JobStatusEnum, int]
    active_agents: int
    stuck_jobs: int
    total_handoffs: int
    waiting_jobs_by_role: list[tuple[str, int]]
    published_to_claimed_pairs: list[tuple[datetime | None, datetime | None]]
    published_to_resolution_pairs: list[tuple[datetime | None, datetime | None]]


@dataclass(slots=True)
class HandoffJobUiItem:
    id: int
    parent_job_id: int | None
    parent_job_summary: str | None
    summary: str
    status: JobStatusEnum
    priority: int
    source_agent_label: str
    assignee_agent_label: str | None
    target_role_label: str
    created_at: datetime


@dataclass(slots=True)
class HandoffJobUiPage:
    items: list[HandoffJobUiItem]
    total: int
    limit: int
    offset: int


@dataclass(slots=True)
class JobEventUiItem:
    event_type: str
    previous_status: JobStatusEnum | None
    current_status: JobStatusEnum
    actor_agent_label: str | None
    payload_json: dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class HandoffJobUiDetailItem:
    id: int
    parent_job_id: int | None
    parent_job_summary: str | None
    summary: str
    context_payload: dict[str, Any]
    status: JobStatusEnum
    priority: int
    source_agent_label: str
    assignee_agent_label: str | None
    target_role_label: str
    constraints: list[Any]
    failure_reason: str | None
    blocked_reason: str | None
    published_at: datetime
    claimed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    blocked_at: datetime | None
    cancelled_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
