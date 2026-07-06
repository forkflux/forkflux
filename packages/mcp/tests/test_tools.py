import json
from typing import Any
from unittest.mock import patch

import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.exceptions import ToolError
from forkflux_mcp.constants import JobChangeStatusEnum, JobPriorityEnum
from forkflux_mcp.main import TargetRoleEnum
from forkflux_mcp.schemas import JobArtifact


def _assert_tool_result_envelope(result, expected_payload: dict[str, Any]) -> None:
    assert result.is_error is False
    assert result.data == expected_payload
    assert result.structured_content == expected_payload
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert json.loads(result.content[0].text) == expected_payload


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
            "my_role_only": True,
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
                "target_role_key": TargetRoleEnum.qa_agent,
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
        "details": {"id": 77, "status": "claimed"},
    }

    with patch("forkflux_mcp.main._api_request", return_value=expected_payload) as mock_api_request:
        result = await client.call_tool("forkflux_claim_job", arguments={"job_id": 77})

    mock_api_request.assert_called_once_with("POST", "/jobs/77/claim")
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
        json_data={"status": "in_progress", "failure_reason": None},
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
        },
    )
    _assert_tool_result_envelope(result, expected_payload)
