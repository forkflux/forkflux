from typing import Any

from pydantic import BaseModel


class JobArtifact(BaseModel):
    type: str
    uri: str
    checksum: str | None
    metadata_json: dict[str, Any]
