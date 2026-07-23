from forkflux_api.jobs.constants import JobPriorityEnum
from forkflux_api.jobs.dto import HandoffJobWithArtifacts
from forkflux_api.jobs.mcp_schemas import HandoffJobWithArtifactsItem, JobArtifact


def handoff_job_to_response_model(entity: HandoffJobWithArtifacts) -> HandoffJobWithArtifactsItem:
    job = entity["job"]
    artifacts = entity["artifacts"]

    return HandoffJobWithArtifactsItem(
        id=job.job_details.id,
        parent_job_id=job.job_details.parent_job_id,
        summary=job.job_details.summary,
        context_payload=job.job_details.context_payload,
        status=job.job_details.status,
        priority=JobPriorityEnum(job.job_details.priority),
        source_agent_label=job.source_agent_label,
        assignee_agent_label=job.assignee_agent_label,
        target_role_key=job.target_role_key,
        constraints=job.job_details.constraints,
        artifacts=[
            JobArtifact(
                type=artifact.artifact_type,
                uri=artifact.artifact_uri,
                checksum=artifact.artifact_checksum,
                metadata_json=artifact.metadata_json,
            )
            for artifact in artifacts
        ],
        failure_reason=job.job_details.failure_reason,
        blocked_reason=job.job_details.blocked_reason,
        unblock_reason=job.job_details.unblock_reason,
        published_at=job.job_details.published_at,
        claimed_at=job.job_details.claimed_at,
        started_at=job.job_details.started_at,
        completed_at=job.job_details.completed_at,
        failed_at=job.job_details.failed_at,
        blocked_at=job.job_details.blocked_at,
        unblocked_at=job.job_details.unblocked_at,
        cancelled_at=job.job_details.cancelled_at,
        expires_at=job.job_details.expires_at,
        created_at=job.job_details.created_at,
        updated_at=job.job_details.updated_at,
    )
