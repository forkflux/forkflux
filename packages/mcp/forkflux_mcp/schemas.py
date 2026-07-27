from typing import Any

from pydantic import BaseModel, Field

from forkflux_mcp.constants import JobPriorityEnum


class JobArtifact(BaseModel):
    type: str = Field(..., description="Artifact type (eg: 'file', 'git_diff', 'uri', 'image_snapshot')")
    uri: str = Field(
        ..., description="Uniform resource identifier (for example: 'file:///src/main.py' or 'git://diff_hash')"
    )
    checksum: str | None = Field(
        None, description="SHA-256 or other hash to verify the integrity of the artifact on the target machine"
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (file size, blast radius, parsing instructions)"
    )


class RoutingRule(BaseModel):
    """A single conditional routing rule — a job template to be auto-created
    when the parent job transitions to COMPLETED.
    """

    target_role_key: str = Field(..., description="The required specialization for the auto-created job.")
    summary: str = Field(..., description="A concise, human-readable title of the auto-created job.")
    context_payload: dict[str, Any] = Field(
        ..., description="A highly detailed, structured JSON dictionary for the auto-created job."
    )
    constraints: list[str] = Field(
        ..., description="A list of strict constraints or execution boundaries for the auto-created job."
    )
    priority: JobPriorityEnum = Field(..., description="The urgency of the auto-created job.")
    artifacts: list[JobArtifact] = Field(
        default_factory=list, description="A list of external resources attached to the auto-created job."
    )
