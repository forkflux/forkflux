from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from forkflux_api.jobs.constants import JobListOrderEnum, JobPriorityEnum, JobStatusEnum
from forkflux_api.jobs.dependencies import get_handoff_job_service
from forkflux_api.jobs.dto import HandoffJobFilterParams
from forkflux_api.jobs.exceptions import HandoffJobConflictError, HandoffJobNotFoundError
from forkflux_api.jobs.services import HandoffJobService
from forkflux_api.jobs.ui_schemas import (
    JobArtifactUiItem,
    JobEventUiItem,
    JobStatusCountsResponse,
    JobUiDetailItem,
    JobUiListItem,
    JobUiListResponse,
    UnblockJobRequest,
    UnblockJobResponse,
)

router = APIRouter(prefix="/jobs", tags=["ui"])


@router.get("", response_model=JobUiListResponse)
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    status: list[JobStatusEnum] | None = Query(default=None),
    order: list[JobListOrderEnum] = Query(default=[JobListOrderEnum.CREATED_AT_ASC]),
    offset: int = Query(0, ge=0),
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    statuses = status or []
    filter_params = HandoffJobFilterParams(
        limit=limit,
        statuses=statuses,
        target_role_ids=[],
        order=order,
        offset=offset,
    )
    page = await job_service.list_ui_jobs(filter_params=filter_params)
    return JobUiListResponse(
        items=[
            JobUiListItem(
                id=item.id,
                parent_job_id=item.parent_job_id,
                parent_job_summary=item.parent_job_summary,
                summary=item.summary,
                status=item.status,
                priority=item.priority,
                source_agent_label=item.source_agent_label,
                assignee_agent_label=item.assignee_agent_label,
                target_role_label=item.target_role_label,
                created_at=item.created_at,
            )
            for item in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/counts", response_model=JobStatusCountsResponse)
async def get_job_counts(
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    status_counts = await job_service.count_jobs_by_status()
    return JobStatusCountsResponse(counts=status_counts)


@router.get("/{job_id}", response_model=JobUiDetailItem)
async def get_job(
    job_id: int,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    try:
        entity = await job_service.get_ui_job_with_artifacts_and_events(job_id)
    except HandoffJobNotFoundError:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=HandoffJobNotFoundError.msg)

    job = entity["job"]
    artifacts = entity["artifacts"]
    events = entity["events"]

    return JobUiDetailItem(
        id=job.id,
        parent_job_id=job.parent_job_id,
        parent_job_summary=job.parent_job_summary,
        summary=job.summary,
        context_payload=job.context_payload,
        status=job.status,
        priority=JobPriorityEnum(job.priority),
        source_agent_label=job.source_agent_label,
        assignee_agent_label=job.assignee_agent_label,
        target_role_label=job.target_role_label,
        constraints=job.constraints,
        artifacts=[
            JobArtifactUiItem(
                id=artifact.id,
                artifact_type=artifact.artifact_type,
                artifact_uri=artifact.artifact_uri,
                artifact_checksum=artifact.artifact_checksum,
                metadata_json=artifact.metadata_json,
                created_at=artifact.created_at,
            )
            for artifact in artifacts
        ],
        events=[
            JobEventUiItem(
                event_type=event.event_type,
                current_status=event.current_status,
                actor_agent_label=event.actor_agent_label,
                payload_json=event.payload_json,
                created_at=event.created_at,
            )
            for event in events
        ],
        failure_reason=job.failure_reason,
        blocked_reason=job.blocked_reason,
        unblock_reason=job.unblock_reason,
        published_at=job.published_at,
        claimed_at=job.claimed_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        failed_at=job.failed_at,
        blocked_at=job.blocked_at,
        unblocked_at=job.unblocked_at,
        cancelled_at=job.cancelled_at,
        expires_at=job.expires_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.post("/{job_id}/unblock", response_model=UnblockJobResponse)
async def unblock_job(
    job_id: int,
    data: UnblockJobRequest,
    job_service: HandoffJobService = Depends(get_handoff_job_service),
):
    try:
        previous_status, new_status = await job_service.change_job_status(
            job_id=job_id,
            status=JobStatusEnum.UNBLOCKED,
            unblock_reason=data.unblock_reason,
        )
    except HandoffJobNotFoundError:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=HandoffJobNotFoundError.msg)
    except HandoffJobConflictError:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Handoff job cannot be unblocked from its current status.",
        )

    return UnblockJobResponse(
        job_id=job_id,
        previous_status=previous_status,
        new_status=new_status,
        unblock_reason=data.unblock_reason,
    )
