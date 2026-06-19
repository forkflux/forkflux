from dataclasses import dataclass
from typing import Any, TypedDict

from forkflux_api.jobs.constants import JobListOrderEnum, JobPriorityEnum, JobStatusEnum
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
class JobArtifactCreate:
    job_id: int
    artifact_type: str
    artifact_uri: str
    artifact_checksum: str | None
    metadata_json: dict[str, Any]


@dataclass(slots=True)
class JobEventCreate:
    job_id: int
    event_type: str
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


@dataclass(slots=True)
class HandoffJobFilterParams:
    limit: int
    status: JobStatusEnum | None
    target_role_id: int | None
    order: list[JobListOrderEnum]
