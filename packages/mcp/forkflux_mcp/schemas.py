from typing import Any

from pydantic import BaseModel, Field


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
