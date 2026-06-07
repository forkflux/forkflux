from typing import Any

from pydantic import BaseModel, ConfigDict
from src.jobs.constants import JobPriorityEnum


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
