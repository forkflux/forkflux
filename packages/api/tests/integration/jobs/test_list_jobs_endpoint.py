import hashlib
from datetime import datetime, timedelta, timezone

from forkflux_api.agents.models import AgentIdentity
from forkflux_api.jobs.constants import JobPriorityEnum, JobStatusEnum
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.factories import AgentApiTokenFactory, AgentIdentityFactory, HandoffJobFactory, TargetRoleFactory


async def _create_auth_context(db_session: AsyncSession, raw_token: str) -> AgentIdentity:
    source_role = await TargetRoleFactory.create(
        db_session,
        role_key=f"list-jobs-source-role-{raw_token}",
        role_label="List jobs source role",
    )
    source_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=source_role.id,
        agent_label=f"list-jobs-source-agent-{raw_token}",
    )
    await AgentApiTokenFactory.create(
        db_session,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        agent_id=source_agent.id,
        is_active=True,
    )
    return source_agent


async def test_list_jobs_returns_200_with_ascending_created_order_and_mapped_fields(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-token"
    source_agent = await _create_auth_context(db_session, raw_token)
    source_role_key = f"list-jobs-source-role-{raw_token}"

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-reviewer-role",
        role_label="List jobs reviewer role",
    )
    operator_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-operator-role",
        role_label="List jobs operator role",
    )
    assignee_agent = await AgentIdentityFactory.create(
        db_session,
        role_id=operator_role.id,
        agent_label="list-jobs-assignee-agent",
    )

    oldest_job = await HandoffJobFactory.create(
        db_session,
        summary="Oldest list job",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.NORMAL.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        assignee_agent_id=None,
        created_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    newest_job = await HandoffJobFactory.create(
        db_session,
        summary="Newest list job",
        status=JobStatusEnum.CLAIMED,
        priority=JobPriorityEnum.HIGH.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        assignee_agent_id=assignee_agent.id,
        created_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Different role should be excluded by default",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.NORMAL.value,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        assignee_agent_id=None,
        created_at=datetime(2026, 3, 3, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 3, tzinfo=timezone.utc),
        published_at=datetime(2026, 3, 3, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [oldest_job.id, newest_job.id]

    assert body[0] == {
        "id": oldest_job.id,
        "summary": oldest_job.summary,
        "status": JobStatusEnum.PUBLISHED.value,
        "priority": JobPriorityEnum.NORMAL.value,
        "source_agent_label": source_agent.agent_label,
        "assignee_agent_label": None,
        "target_role_key": source_role_key,
        "created_at": oldest_job.created_at.isoformat().replace("+00:00", "Z"),
    }
    assert body[1] == {
        "id": newest_job.id,
        "summary": newest_job.summary,
        "status": JobStatusEnum.CLAIMED.value,
        "priority": JobPriorityEnum.HIGH.value,
        "source_agent_label": source_agent.agent_label,
        "assignee_agent_label": assignee_agent.agent_label,
        "target_role_key": source_role_key,
        "created_at": newest_job.created_at.isoformat().replace("+00:00", "Z"),
    }


async def test_list_jobs_filters_by_status_and_target_role_key_when_my_role_only_is_false(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-filter-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-filter-reviewer",
        role_label="List jobs filter reviewer",
    )
    operator_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-filter-operator",
        role_label="List jobs filter operator",
    )

    matching_job = await HandoffJobFactory.create(
        db_session,
        summary="Matching filter",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Non matching status",
        status=JobStatusEnum.CLAIMED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 2, tzinfo=timezone.utc),
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Non matching role",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=operator_role.id,
        created_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 3, tzinfo=timezone.utc),
    )

    response = await client.get(
        f"/api/v1/jobs?my_role_only=false&status={JobStatusEnum.PUBLISHED.value}&target_role_key={reviewer_role.role_key}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == matching_job.id
    assert body[0]["status"] == JobStatusEnum.PUBLISHED.value
    assert body[0]["target_role_key"] == reviewer_role.role_key


async def test_list_jobs_with_my_role_only_false_and_no_target_role_key_returns_cross_role_items(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-cross-role-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-cross-role-reviewer",
        role_label="List jobs cross role reviewer",
    )
    operator_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-cross-role-operator",
        role_label="List jobs cross role operator",
    )

    first_matching_job = await HandoffJobFactory.create(
        db_session,
        summary="Cross role first matching",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
    )
    second_matching_job = await HandoffJobFactory.create(
        db_session,
        summary="Cross role second matching",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=operator_role.id,
        created_at=datetime(2026, 4, 11, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 11, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 11, tzinfo=timezone.utc),
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Cross role non matching status",
        status=JobStatusEnum.CLAIMED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 4, 12, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 12, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 12, tzinfo=timezone.utc),
    )

    response = await client.get(
        f"/api/v1/jobs?my_role_only=false&status={JobStatusEnum.PUBLISHED.value}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [first_matching_job.id, second_matching_job.id]


async def test_list_jobs_filters_by_multiple_repeated_status_query_params(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-multi-status-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    published_job = await HandoffJobFactory.create(
        db_session,
        summary="Repeated status published",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 15, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 15, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 15, tzinfo=timezone.utc),
    )
    claimed_job = await HandoffJobFactory.create(
        db_session,
        summary="Repeated status claimed",
        status=JobStatusEnum.CLAIMED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 16, tzinfo=timezone.utc),
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Repeated status excluded",
        status=JobStatusEnum.COMPLETED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 17, tzinfo=timezone.utc),
    )

    response = await client.get(
        f"/api/v1/jobs?status={JobStatusEnum.PUBLISHED.value}&status={JobStatusEnum.CLAIMED.value}",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [published_job.id, claimed_job.id]


async def test_list_jobs_treats_omitted_status_as_empty_status_list(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-empty-status-filter-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    published_job = await HandoffJobFactory.create(
        db_session,
        summary="Omitted status published",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 18, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 18, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 18, tzinfo=timezone.utc),
    )
    claimed_job = await HandoffJobFactory.create(
        db_session,
        summary="Omitted status claimed",
        status=JobStatusEnum.CLAIMED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [published_job.id, claimed_job.id]


async def test_list_jobs_with_my_role_only_true_and_empty_target_role_key_treats_it_as_omitted(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-empty-role-my-role-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-empty-role-my-role-reviewer",
        role_label="List jobs empty role my role reviewer",
    )

    matching_job = await HandoffJobFactory.create(
        db_session,
        summary="My role only matching",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 20, tzinfo=timezone.utc),
    )
    await HandoffJobFactory.create(
        db_session,
        summary="Other role should be excluded",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 4, 21, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 21, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 21, tzinfo=timezone.utc),
    )

    response = await client.get(
        f"/api/v1/jobs?limit=10&status={JobStatusEnum.PUBLISHED.value}&target_role_key=&my_role_only=true",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [matching_job.id]


async def test_list_jobs_with_my_role_only_false_and_empty_target_role_key_treats_it_as_omitted(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-empty-role-cross-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    reviewer_role = await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-empty-role-cross-reviewer",
        role_label="List jobs empty role cross reviewer",
    )

    first_matching_job = await HandoffJobFactory.create(
        db_session,
        summary="Cross role first matching with empty key",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        updated_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        published_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
    )
    second_matching_job = await HandoffJobFactory.create(
        db_session,
        summary="Cross role second matching with empty key",
        status=JobStatusEnum.PUBLISHED,
        source_agent_id=source_agent.id,
        target_role_id=reviewer_role.id,
        created_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 5, 1, tzinfo=timezone.utc),
    )

    response = await client.get(
        f"/api/v1/jobs?my_role_only=false&status={JobStatusEnum.PUBLISHED.value}&target_role_key=",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [first_matching_job.id, second_matching_job.id]


async def test_list_jobs_applies_limit_and_preserves_ascending_created_order(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-limit-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    await TargetRoleFactory.create(
        db_session,
        role_key="list-jobs-limit-role",
        role_label="List jobs limit role",
    )

    first_job = None
    second_job = None
    base_dt = datetime(2026, 5, 1, tzinfo=timezone.utc)
    for day_offset in range(51):
        current_dt = base_dt + timedelta(days=day_offset)
        created_job = await HandoffJobFactory.create(
            db_session,
            source_agent_id=source_agent.id,
            target_role_id=source_agent.role_id,
            created_at=current_dt,
            updated_at=current_dt,
            published_at=current_dt,
        )
        if day_offset == 0:
            first_job = created_job
        if day_offset == 1:
            second_job = created_job

    response = await client.get(
        "/api/v1/jobs?limit=50",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert first_job is not None
    assert second_job is not None
    assert len(body) == 50
    assert body[0]["id"] == first_job.id
    assert body[1]["id"] == second_job.id


async def test_list_jobs_orders_by_priority_desc_then_created_at_asc_when_order_is_repeated(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-order-priority-then-created-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    first_expected = await HandoffJobFactory.create(
        db_session,
        summary="Priority high earliest",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.HIGH.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )
    third_expected = await HandoffJobFactory.create(
        db_session,
        summary="Priority high latest",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.HIGH.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
        published_at=datetime(2026, 6, 3, tzinfo=timezone.utc),
    )
    second_expected = await HandoffJobFactory.create(
        db_session,
        summary="Priority normal middle",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.NORMAL.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/api/v1/jobs?order=priority_desc&order=created_at_asc",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [first_expected.id, third_expected.id, second_expected.id]


async def test_list_jobs_orders_by_created_at_asc_then_priority_desc_when_order_is_repeated(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-order-created-then-priority-token"
    source_agent = await _create_auth_context(db_session, raw_token)

    first_expected = await HandoffJobFactory.create(
        db_session,
        summary="Created same day high",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.HIGH.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    second_expected = await HandoffJobFactory.create(
        db_session,
        summary="Created same day normal",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.NORMAL.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        published_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    third_expected = await HandoffJobFactory.create(
        db_session,
        summary="Created next day urgent",
        status=JobStatusEnum.PUBLISHED,
        priority=JobPriorityEnum.URGENT.value,
        source_agent_id=source_agent.id,
        target_role_id=source_agent.role_id,
        created_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
        published_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    response = await client.get(
        "/api/v1/jobs?order=created_at_asc&order=priority_desc",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["id"] for item in body] == [first_expected.id, second_expected.id, third_expected.id]


async def test_list_jobs_returns_422_when_order_contains_invalid_value(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-invalid-order-token"
    await _create_auth_context(db_session, raw_token)

    response = await client.get(
        "/api/v1/jobs?order=priority_desc&order=unknown",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["query", "order", 1]


async def test_list_jobs_returns_403_when_bearer_token_is_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/jobs")

    assert response.status_code == 403
    assert response.json() == {"detail": "Not authenticated"}


async def test_list_jobs_returns_401_for_invalid_bearer_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    valid_raw_token = "some-other-valid-list-jobs-token"
    await _create_auth_context(db_session, valid_raw_token)

    response = await client.get(
        "/api/v1/jobs",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_list_jobs_returns_422_when_target_role_key_is_invalid(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    raw_token = "valid-list-jobs-invalid-role-token"
    await _create_auth_context(db_session, raw_token)

    response = await client.get(
        "/api/v1/jobs?my_role_only=false&target_role_key=missing-role-key",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "loc": ["query", "target_role_key"],
                "msg": "Target role is invalid.",
                "type": "target_role.invalid",
                "input": "missing-role-key",
                "ctx": {},
            }
        ]
    }
