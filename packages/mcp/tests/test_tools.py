import json
from typing import Any
from unittest.mock import patch

import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError
from forkflux_mcp.constants import JobChangeStatusEnum, JobPriorityEnum
from forkflux_mcp.schemas import JobArtifact


def _assert_tool_result_envelope(result, expected_payload: dict[str, Any]) -> None:
    assert result.is_error is False
    assert result.data == expected_payload
    assert result.structured_content == expected_payload
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert json.loads(result.content[0].text) == expected_payload


def _collect_enum_values(value: object) -> set[str]:
    if isinstance(value, dict):
        dict_values = {item for item in value.get("enum", []) if isinstance(item, str)}
        for nested_value in value.values():
            dict_values.update(_collect_enum_values(nested_value))
        return dict_values
    if isinstance(value, list):
        list_values: set[str] = set()
        for nested_value in value:
            list_values.update(_collect_enum_values(nested_value))
        return list_values
    return set()


def _get_input_schema(tool: object) -> dict[str, Any]:
    schema = getattr(tool, "inputSchema", None)
    if schema is None:
        schema = getattr(tool, "input_schema")
    assert isinstance(schema, dict)
    return schema


async def test_role_dependent_tool_schemas_expose_api_roles(
    client: Client[FastMCPTransport],
) -> None:
    tools = await client.list_tools()
    tools_by_name = {tool.name: tool for tool in tools}
    expected_role_keys = {"qa_agent", "security_reviewer"}

    for tool_name in ("forkflux_create_job", "forkflux_list_jobs", "forkflux_claim_next_job"):
        assert tool_name in tools_by_name
        schema = _get_input_schema(tools_by_name[tool_name])
        assert expected_role_keys <= _collect_enum_values(schema)


async def test_list_jobs_calls_api_request_with_default_params_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": [{"id": 11, "status": "published"}],
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool("forkflux_list_jobs")

    mock_api_request.assert_called_once_with(
        "GET",
        "/jobs?order=priority_desc&order=created_at_asc",
        params={
            "limit": 50,
            "status": "published",
            "target_role_key": None,
            "my_roles_only": True,
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_create_job_calls_api_request_with_full_payload_and_returns_result(
    client: Client[FastMCPTransport],
) -> None:
    artifacts_payload = [
        {
            "type": "git_commit",
            "uri": "git://repo/commit/abc123",
            "checksum": "sha256:abc123",
            "metadata_json": {"branch": "feature/mcp-tests"},
        },
        {
            "type": "s3",
            "uri": "s3://bucket/path/to/logs.json",
            "checksum": None,
            "metadata_json": {"content_type": "application/json"},
        },
    ]
    expected_artifacts = [
        JobArtifact(
            type="git_commit",
            uri="git://repo/commit/abc123",
            checksum="sha256:abc123",
            metadata_json={"branch": "feature/mcp-tests"},
        ).model_dump(),
        JobArtifact(
            type="s3",
            uri="s3://bucket/path/to/logs.json",
            checksum=None,
            metadata_json={"content_type": "application/json"},
        ).model_dump(),
    ]

    expected_payload = {
        "success": True,
        "details": {"id": 101, "status": "published"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_create_job",
            arguments={
                "summary": "Investigate flaky integration test",
                "context_payload": {"suite": "jobs", "failing_case": "test_create_job_endpoint"},
                "target_role_key": "qa_agent",
                "constraints": ["do-not-modify-production-data", "keep-runtime-under-5-minutes"],
                "artifacts": artifacts_payload,
                "priority": JobPriorityEnum.HIGH,
                "parent_job_id": 42,
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs",
        json_data={
            "summary": "Investigate flaky integration test",
            "context_payload": {"suite": "jobs", "failing_case": "test_create_job_endpoint"},
            "target_role_key": "qa_agent",
            "constraints": ["do-not-modify-production-data", "keep-runtime-under-5-minutes"],
            "artifacts": expected_artifacts,
            "priority": JobPriorityEnum.HIGH,
            "parent_job_id": 42,
            "blocked_by": [],
            "routing_rules": None,
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_create_job_with_routing_rules_passes_them_to_api_request(
    client: Client[FastMCPTransport],
) -> None:
    """forkflux_create_job must serialize routing_rules and pass them to _api_request."""
    routing_rules_payload = [
        {
            "target_role_key": "security_reviewer",
            "summary": "Review the completed work",
            "context_payload": {"review_type": "security_audit"},
            "constraints": ["must approve before merge"],
            "priority": JobPriorityEnum.NORMAL,
            "artifacts": [],
        }
    ]
    expected_routing_rules = [
        {
            "target_role_key": "security_reviewer",
            "summary": "Review the completed work",
            "context_payload": {"review_type": "security_audit"},
            "constraints": ["must approve before merge"],
            "priority": JobPriorityEnum.NORMAL,
            "artifacts": [],
        }
    ]

    expected_payload = {
        "success": True,
        "details": {"id": 102, "status": "published"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_create_job",
            arguments={
                "summary": "Build the auth feature",
                "context_payload": {"feature": "auth"},
                "target_role_key": "qa_agent",
                "constraints": ["deadline:today"],
                "artifacts": [],
                "priority": JobPriorityEnum.HIGH,
                "routing_rules": routing_rules_payload,
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs",
        json_data={
            "summary": "Build the auth feature",
            "context_payload": {"feature": "auth"},
            "target_role_key": "qa_agent",
            "constraints": ["deadline:today"],
            "artifacts": [],
            "priority": JobPriorityEnum.HIGH,
            "parent_job_id": None,
            "blocked_by": [],
            "routing_rules": expected_routing_rules,
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_create_job_rejects_invalid_target_role_key_and_does_not_call_api_request(
    client: Client[FastMCPTransport],
) -> None:
    with patch("forkflux_mcp.main._api_request") as mock_api_request:
        with pytest.raises(ToolError, match="target_role_key"):
            await client.call_tool(
                "forkflux_create_job",
                arguments={
                    "summary": "Investigate flaky integration test",
                    "context_payload": {"suite": "jobs", "failing_case": "test_create_job_endpoint"},
                    "target_role_key": "invalid_role",
                    "constraints": ["do-not-modify-production-data"],
                    "artifacts": [],
                    "priority": JobPriorityEnum.HIGH,
                    "parent_job_id": 42,
                },
            )

    mock_api_request.assert_not_called()


async def test_claim_job_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"id": 77, "status": "in_progress"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool("forkflux_claim_job", arguments={"job_id": 77})

    mock_api_request.assert_called_once_with("POST", "/jobs/77/claim")
    _assert_tool_result_envelope(result, expected_payload)


async def test_claim_next_job_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"id": 88, "status": "in_progress", "summary": "Fix CI pipeline"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_claim_next_job",
            arguments={"target_role_key": "qa_agent"},
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs/claim-next",
        json_data={"target_role_key": "qa_agent"},
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_job_details_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"id": 77, "status": "in_progress", "summary": "Investigate flaky test"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool("forkflux_job_details", arguments={"job_id": 77})

    mock_api_request.assert_called_once_with("GET", "/jobs/77")
    _assert_tool_result_envelope(result, expected_payload)


async def test_change_job_status_in_progress_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"id": 77, "status": "in_progress"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_change_job_status",
            arguments={
                "job_id": 77,
                "status": JobChangeStatusEnum.IN_PROGRESS,
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs/77/status",
        json_data={"status": "in_progress", "failure_reason": None, "blocked_reason": None},
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_change_job_status_blocked_calls_api_request_with_blocked_reason_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {
            "id": 77,
            "status": "blocked",
            "blocked_reason": "waiting on upstream API to be deployed",
        },
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_change_job_status",
            arguments={
                "job_id": 77,
                "status": JobChangeStatusEnum.BLOCKED,
                "blocked_reason": "waiting on upstream API to be deployed",
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs/77/status",
        json_data={
            "status": "blocked",
            "failure_reason": None,
            "blocked_reason": "waiting on upstream API to be deployed",
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_change_job_status_failed_calls_api_request_with_failure_reason_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {
            "id": 77,
            "status": "failed",
            "failure_reason": "pytest collection failed due to missing fixture",
        },
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_change_job_status",
            arguments={
                "job_id": 77,
                "status": JobChangeStatusEnum.FAILED,
                "failure_reason": "pytest collection failed due to missing fixture",
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs/77/status",
        json_data={
            "status": "failed",
            "failure_reason": "pytest collection failed due to missing fixture",
            "blocked_reason": None,
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_create_job_with_blocked_by_calls_api_request_with_correct_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"job_id": 201, "status": "pending"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_create_job",
            arguments={
                "summary": "Fan-in job waiting for upstream",
                "context_payload": {"task": "qa_review"},
                "target_role_key": "qa_agent",
                "constraints": ["deadline:today"],
                "artifacts": [],
                "priority": JobPriorityEnum.NORMAL,
                "parent_job_id": None,
                "blocked_by": [101, 102],
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs",
        json_data={
            "summary": "Fan-in job waiting for upstream",
            "context_payload": {"task": "qa_review"},
            "target_role_key": "qa_agent",
            "constraints": ["deadline:today"],
            "artifacts": [],
            "priority": JobPriorityEnum.NORMAL,
            "parent_job_id": None,
            "blocked_by": [101, 102],
            "routing_rules": None,
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_reject_job_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"job_id": 300, "original_job_id": 200, "retry_count": 1},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_reject_job",
            arguments={
                "job_id": 150,
                "target_job_id": 200,
                "reason": "Tests failed on edge case",
            },
        )

    mock_api_request.assert_called_once_with(
        "POST",
        "/jobs/150/reject",
        json_data={"target_job_id": 200, "reason": "Tests failed on edge case"},
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_get_reopen_context_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {
            "job_id": 300,
            "original_job_id": 200,
            "rejected_by_job_id": 150,
            "retry_count": 1,
            "max_retries": 3,
            "rejection_reason": "Tests failed on edge case",
            "summary": "[Retry 1] Fix the bug",
            "constraints": ["deadline:today"],
            "target_role_key": "backend",
        },
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_get_reopen_context",
            arguments={"job_id": 300},
        )

    mock_api_request.assert_called_once_with("GET", "/jobs/300/reopen-context")
    _assert_tool_result_envelope(result, expected_payload)


async def test_update_job_with_context_payload_only_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"job_id": 55, "message": "job with job_id 55 updated successfully"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_update_job",
            arguments={
                "job_id": 55,
                "context_payload": {"ticket_id": "TCK-2", "extra": "data"},
            },
        )

    mock_api_request.assert_called_once_with(
        "PATCH",
        "/jobs/55",
        json_data={
            "context_payload": {"ticket_id": "TCK-2", "extra": "data"},
            "constraints": None,
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_update_job_with_constraints_only_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"job_id": 55, "message": "job with job_id 55 updated successfully"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_update_job",
            arguments={
                "job_id": 55,
                "constraints": ["deadline:tomorrow", "priority:high"],
            },
        )

    mock_api_request.assert_called_once_with(
        "PATCH",
        "/jobs/55",
        json_data={
            "context_payload": None,
            "constraints": ["deadline:tomorrow", "priority:high"],
        },
    )
    _assert_tool_result_envelope(result, expected_payload)


async def test_update_job_with_both_fields_calls_api_request_with_expected_contract_and_returns_payload(
    client: Client[FastMCPTransport],
) -> None:
    expected_payload = {
        "success": True,
        "details": {"job_id": 55, "message": "job with job_id 55 updated successfully"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool(
            "forkflux_update_job",
            arguments={
                "job_id": 55,
                "context_payload": {"ticket_id": "TCK-2"},
                "constraints": ["deadline:tomorrow"],
            },
        )

    mock_api_request.assert_called_once_with(
        "PATCH",
        "/jobs/55",
        json_data={
            "context_payload": {"ticket_id": "TCK-2"},
            "constraints": ["deadline:tomorrow"],
        },
    )
    _assert_tool_result_envelope(result, expected_payload)
