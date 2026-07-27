from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from forkflux_api.agents.dependencies import get_target_role_service
from forkflux_api.agents.exceptions import TargetRoleNotFoundError
from forkflux_api.agents.models import TargetRole
from forkflux_api.agents.services import TargetRoleService
from forkflux_api.database import get_session
from forkflux_api.jobs.api_exceptions import (
    BlockedByJobValidationError,
    ParentJobValidationError,
    RoutingRuleValidationError,
    TargetRoleValidationError,
)
from forkflux_api.jobs.dto import HandoffJobItem, JobArtifactCreate, RoutingRuleCreate
from forkflux_api.jobs.exceptions import HandoffJobNotFoundError
from forkflux_api.jobs.mcp_schemas import HandoffJobClaimNextRequest, HandoffJobCreateRequest
from forkflux_api.jobs.repositories import (
    HandoffJobRepository,
    JobArtifactRepository,
    JobDependencyRepository,
    JobEventRepository,
)
from forkflux_api.jobs.services import HandoffJobService


def get_trace_id(request: Request) -> str:
    return request.state.trace_id


async def get_handoff_job_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> HandoffJobRepository:
    return HandoffJobRepository(session=session, trace_id=trace_id)


async def get_job_artifact_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> JobArtifactRepository:
    return JobArtifactRepository(session=session, trace_id=trace_id)


async def get_job_event_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> JobEventRepository:
    return JobEventRepository(session=session, trace_id=trace_id)


async def get_job_dependency_repo(
    session: AsyncSession = Depends(get_session), trace_id: str = Depends(get_trace_id)
) -> JobDependencyRepository:
    return JobDependencyRepository(session=session, trace_id=trace_id)


def get_handoff_job_service(
    repository: HandoffJobRepository = Depends(get_handoff_job_repo),
    job_artifact_repo: JobArtifactRepository = Depends(get_job_artifact_repo),
    job_event_repo: JobEventRepository = Depends(get_job_event_repo),
    job_dependency_repo: JobDependencyRepository = Depends(get_job_dependency_repo),
    trace_id: str = Depends(get_trace_id),
) -> HandoffJobService:
    return HandoffJobService(
        handoff_job_repo=repository,
        job_artifact_repo=job_artifact_repo,
        job_event_repo=job_event_repo,
        job_dependency_repo=job_dependency_repo,
        trace_id=trace_id,
    )


async def validate_parent_job(
    job_data: HandoffJobCreateRequest, service: HandoffJobService = Depends(get_handoff_job_service)
) -> HandoffJobItem | None:
    if job_data.parent_job_id is None:
        return None

    try:
        parent_job = await service.get_job(job_id=job_data.parent_job_id)
        return parent_job
    except HandoffJobNotFoundError:
        raise ParentJobValidationError(field_name="parent_job_id", value=job_data.parent_job_id)


async def validate_blocked_by_jobs(
    job_data: HandoffJobCreateRequest, service: HandoffJobService = Depends(get_handoff_job_service)
) -> list[HandoffJobItem] | None:
    if not job_data.blocked_by:
        return None

    # Single batch query: count how many of the blocked_by IDs exist.
    # Deduplication is handled centrally in HandoffJobService.create_job().
    existing_count = await service.count_existing_job_ids(job_data.blocked_by)
    if existing_count != len(set(job_data.blocked_by)):
        # Find the first missing ID for a helpful error message.
        for upstream_id in job_data.blocked_by:
            try:
                await service.get_job(job_id=upstream_id)
            except HandoffJobNotFoundError:
                raise BlockedByJobValidationError(field_name="blocked_by", value=upstream_id)

    return None


async def validate_target_role(
    job_data: HandoffJobCreateRequest, service: TargetRoleService = Depends(get_target_role_service)
) -> TargetRole:
    try:
        target_role = await service.get_by_role_key(role_key=job_data.target_role_key)
        return target_role
    except TargetRoleNotFoundError:
        raise TargetRoleValidationError(field_name="target_role_key", value=job_data.target_role_key)


async def validate_target_role_query_param(
    target_role_key: str | None = None, service: TargetRoleService = Depends(get_target_role_service)
) -> TargetRole | None:
    if target_role_key is None or target_role_key.strip() == "":
        return None

    try:
        role = await service.get_by_role_key(role_key=target_role_key)
        return role
    except TargetRoleNotFoundError:
        raise TargetRoleValidationError(field_name="target_role_key", value=target_role_key, loc="query")


async def validate_target_role_claim_next(
    data: HandoffJobClaimNextRequest, service: TargetRoleService = Depends(get_target_role_service)
) -> TargetRole:
    try:
        return await service.get_by_role_key(role_key=data.target_role_key)
    except TargetRoleNotFoundError:
        raise TargetRoleValidationError(field_name="target_role_key", value=data.target_role_key)


async def validate_routing_rules(
    job_data: HandoffJobCreateRequest, service: TargetRoleService = Depends(get_target_role_service)
) -> list[RoutingRuleCreate] | None:
    """Validate all ``target_role_key`` values in routing rules and resolve them to IDs.

    Returns a list of ``RoutingRuleCreate`` dataclasses with ``target_role_id``
    pre-resolved, or ``None`` if no routing rules were provided. The resolved
    rules are stored in the database so the service does not need role-resolution
    logic at completion time.
    """
    if not job_data.routing_rules:
        return None

    resolved_rules: list[RoutingRuleCreate] = []

    for rule in job_data.routing_rules:
        try:
            target_role = await service.get_by_role_key(role_key=rule.target_role_key)
        except TargetRoleNotFoundError:
            raise RoutingRuleValidationError(
                field_name="target_role_key",
                value=rule.target_role_key,
                loc="body",
                detail=f"Routing rule target role '{rule.target_role_key}' does not exist",
            )

        resolved_rules.append(
            RoutingRuleCreate(
                target_role_id=target_role.id,
                target_role_key=rule.target_role_key,
                summary=rule.summary,
                context_payload=rule.context_payload,
                constraints=rule.constraints,
                priority=rule.priority,
                artifacts=[
                    JobArtifactCreate(
                        job_id=0,  # placeholder — set by the service after job creation
                        artifact_type=artifact.type,
                        artifact_uri=artifact.uri,
                        artifact_checksum=artifact.checksum,
                        metadata_json=artifact.metadata_json,
                    )
                    for artifact in rule.artifacts
                ],
            )
        )

    return resolved_rules
