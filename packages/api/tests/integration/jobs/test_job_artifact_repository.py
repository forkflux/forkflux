from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.jobs.dto import JobArtifactCreate
from src.jobs.exceptions import JobArtifactConflictError
from src.jobs.models import JobArtifact
from src.jobs.repositories import JobArtifactRepository
from tests.factories import AgentIdentityFactory, HandoffJobFactory, JobArtifactFactory, TargetRoleFactory


async def test_job_artifact_repository_init_sets_session_and_logger(db_session: AsyncSession) -> None:
    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")

    assert repository._session is db_session
    assert repository._logger is not None


async def test_job_artifact_repository_create_persists_and_returns_artifact(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-target-role",
        role_label="Job artifact target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-source-role",
        role_label="Job artifact source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-artifact-source-agent",
        role_id=source_role.id,
    )

    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")
    dto = JobArtifactCreate(
        job_id=handoff_job.id,
        artifact_type="document",
        artifact_uri="s3://bucket/job-artifacts/doc-1.pdf",
        artifact_checksum="checksum-abc-123",
        metadata_json={"mime_type": "application/pdf", "size": 1234},
    )

    created_artifact = await repository.create(dto=dto)
    fetched_artifact = await db_session.get(JobArtifact, created_artifact.id)

    assert isinstance(created_artifact, JobArtifact)
    assert created_artifact.id is not None
    assert created_artifact.job_id == handoff_job.id
    assert created_artifact.artifact_type == dto.artifact_type
    assert created_artifact.artifact_uri == dto.artifact_uri
    assert created_artifact.artifact_checksum == dto.artifact_checksum
    assert created_artifact.metadata_json == dto.metadata_json
    assert created_artifact.created_at is not None

    assert fetched_artifact is not None
    assert fetched_artifact.job_id == handoff_job.id
    assert fetched_artifact.artifact_type == dto.artifact_type
    assert fetched_artifact.artifact_uri == dto.artifact_uri
    assert fetched_artifact.artifact_checksum == dto.artifact_checksum
    assert fetched_artifact.metadata_json == dto.metadata_json


async def test_job_artifact_repository_create_raises_conflict_on_integrity_error(
    db_session: AsyncSession,
) -> None:
    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")
    dto = JobArtifactCreate(
        job_id=999_999,
        artifact_type="trace",
        artifact_uri="s3://bucket/job-artifacts/missing-job.trace",
        artifact_checksum=None,
        metadata_json={"source": "integration-test"},
    )

    with pytest.raises(JobArtifactConflictError):
        await repository.create(dto=dto)


async def test_job_artifact_repository_bulk_create_persists_and_returns_artifacts(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-bulk-target-role",
        role_label="Job artifact bulk target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-bulk-source-role",
        role_label="Job artifact bulk source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-artifact-bulk-source-agent",
        role_id=source_role.id,
    )

    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")
    dtos = [
        JobArtifactCreate(
            job_id=handoff_job.id,
            artifact_type="document",
            artifact_uri="s3://bucket/job-artifacts/bulk-doc-1.pdf",
            artifact_checksum="bulk-checksum-1",
            metadata_json={"mime_type": "application/pdf", "size": 100},
        ),
        JobArtifactCreate(
            job_id=handoff_job.id,
            artifact_type="trace",
            artifact_uri="s3://bucket/job-artifacts/bulk-trace-1.json",
            artifact_checksum="bulk-checksum-2",
            metadata_json={"mime_type": "application/json", "size": 200},
        ),
    ]

    created_artifacts = await repository.bulk_create(dtos=dtos)

    assert len(created_artifacts) == 2
    for index, created_artifact in enumerate(created_artifacts):
        dto = dtos[index]
        fetched_artifact = await db_session.get(JobArtifact, created_artifact.id)

        assert isinstance(created_artifact, JobArtifact)
        assert created_artifact.id is not None
        assert created_artifact.job_id == handoff_job.id
        assert created_artifact.artifact_type == dto.artifact_type
        assert created_artifact.artifact_uri == dto.artifact_uri
        assert created_artifact.artifact_checksum == dto.artifact_checksum
        assert created_artifact.metadata_json == dto.metadata_json
        assert created_artifact.created_at is not None

        assert fetched_artifact is not None
        assert fetched_artifact.job_id == handoff_job.id
        assert fetched_artifact.artifact_type == dto.artifact_type
        assert fetched_artifact.artifact_uri == dto.artifact_uri
        assert fetched_artifact.artifact_checksum == dto.artifact_checksum
        assert fetched_artifact.metadata_json == dto.metadata_json


async def test_job_artifact_repository_bulk_create_raises_conflict_on_integrity_error(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-bulk-conflict-target-role",
        role_label="Job artifact bulk conflict target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-bulk-conflict-source-role",
        role_label="Job artifact bulk conflict source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-artifact-bulk-conflict-source-agent",
        role_id=source_role.id,
    )

    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")
    dtos = [
        JobArtifactCreate(
            job_id=handoff_job.id,
            artifact_type="document",
            artifact_uri="s3://bucket/job-artifacts/bulk-conflict-doc-1.pdf",
            artifact_checksum="bulk-conflict-checksum-1",
            metadata_json={"source": "integration-test"},
        ),
        JobArtifactCreate(
            job_id=999_999,
            artifact_type="trace",
            artifact_uri="s3://bucket/job-artifacts/bulk-conflict-missing-job.trace",
            artifact_checksum=None,
            metadata_json={"source": "integration-test"},
        ),
    ]

    with pytest.raises(JobArtifactConflictError):
        await repository.bulk_create(dtos=dtos)

    persisted_valid_artifact = (
        (await db_session.execute(select(JobArtifact).where(JobArtifact.artifact_uri == dtos[0].artifact_uri)))
        .scalars()
        .one_or_none()
    )
    assert persisted_valid_artifact is None


async def test_job_artifact_repository_list_returns_artifacts_for_job_ordered_by_created_at_asc(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-list-target-role",
        role_label="Job artifact list target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-list-source-role",
        role_label="Job artifact list source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-artifact-list-source-agent",
        role_id=source_role.id,
    )

    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    created_at_base = datetime.now(timezone.utc)
    second_artifact = await JobArtifactFactory.create(
        db_session,
        job_id=handoff_job.id,
        artifact_type="trace",
        artifact_uri="s3://bucket/job-artifacts/list-order-2.json",
        artifact_checksum="list-order-checksum-2",
        metadata_json={"order": 2},
        created_at=created_at_base + timedelta(seconds=10),
    )
    first_artifact = await JobArtifactFactory.create(
        db_session,
        job_id=handoff_job.id,
        artifact_type="document",
        artifact_uri="s3://bucket/job-artifacts/list-order-1.pdf",
        artifact_checksum="list-order-checksum-1",
        metadata_json={"order": 1},
        created_at=created_at_base,
    )

    other_handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    await JobArtifactFactory.create(
        db_session,
        job_id=other_handoff_job.id,
        artifact_type="binary",
        artifact_uri="s3://bucket/job-artifacts/list-other-job.bin",
        artifact_checksum="list-order-checksum-other",
        metadata_json={"order": 999},
        created_at=created_at_base + timedelta(seconds=20),
    )

    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")

    listed_artifacts = await repository.list(job_id=handoff_job.id)

    assert [artifact.id for artifact in listed_artifacts] == [first_artifact.id, second_artifact.id]
    assert all(artifact.job_id == handoff_job.id for artifact in listed_artifacts)


async def test_job_artifact_repository_list_returns_empty_list_when_job_has_no_artifacts(
    db_session: AsyncSession,
) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-list-empty-target-role",
        role_label="Job artifact list empty target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-list-empty-source-role",
        role_label="Job artifact list empty source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-artifact-list-empty-source-agent",
        role_id=source_role.id,
    )

    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    repository = JobArtifactRepository(session=db_session, trace_id="trace-123")

    listed_artifacts = await repository.list(job_id=handoff_job.id)

    assert listed_artifacts == []


async def test_job_artifact_factory_creates_artifact_with_valid_job(db_session: AsyncSession) -> None:
    target_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-factory-target-role",
        role_label="Job artifact factory target role",
    )
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key="job-artifact-factory-source-role",
        role_label="Job artifact factory source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        agent_label="job-artifact-factory-source-agent",
        role_id=source_role.id,
    )
    handoff_job = await HandoffJobFactory.create(
        db_session,
        source_agent_id=source_agent.id,
        target_role_id=target_role.id,
    )

    artifact = await JobArtifactFactory.create(
        db_session,
        job_id=handoff_job.id,
    )

    assert isinstance(artifact, JobArtifact)
    assert artifact.id is not None
    assert artifact.job_id == handoff_job.id
