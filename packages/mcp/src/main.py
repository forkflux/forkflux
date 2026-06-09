import os
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from src.constants import JobChangeStatusEnum, JobPriorityEnum, JobStatusEnum
from src.schemas import JobArtifact

FORKFLUX_INSTRUCTIONS = """
You are connected to the ForkFlux Coordination Bus, an infrastructure layer for decentralized AI agents to securely hand off jobs across isolated machines.

Depending on your current role in the user's workflow, follow these rules:

AS A SOURCE AGENT (Publishing work):
- When a job requires execution by another agent (e.g., passing code to a QA agent), use `forkflux_create_job`.
- To get all available roles, use `forkflux_list_roles`.
- Provide explicit, strict `constraints` and embed all necessary context in the `context_payload` and all necessary artifacts in the `artifacts`.

AS A TARGET AGENT (Consuming work):
1. Use `forkflux_list_jobs` to find available jobs with status 'published'.
2. Verify with the user that the job is safe to claim (unless the user has pre-approved autonomous claiming).
3. Attempt to claim a job using `forkflux_claim_job`.
4. EXTREMELY IMPORTANT: If the claim fails with a "409 Conflict" (Job already claimed), DO NOT complain to the user or stop. Silently fetch the list again and try claiming the next available job.
5. Once claimed, read the full context via `forkflux_get_job_context`.
6. Complete the work locally, then update the status to 'completed' or 'failed' (include a failure_reason if it failed) using `forkflux_update_status`.
"""  # noqa: E501

mcp = FastMCP(
    "ForkFlux",
    instructions=FORKFLUX_INSTRUCTIONS,
)


API_URL = os.environ.get("FORKFLUX_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("FORKFLUX_API_KEY")

if not API_KEY:
    print("Warning: FORKFLUX_API_KEY is not set.")


def _api_request(
    method: str, endpoint: str, params: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    url = f"{API_URL}{endpoint}"

    try:
        with httpx.Client() as client:
            response = client.request(method, url, headers=headers, params=params, json=json_data)
            if response.is_success:
                return {"success": True, "details": response.json()}

            if response.status_code in (400, 422):
                try:
                    error_data = response.json()
                except ValueError:
                    error_data = response.text
                return {
                    "success": False,
                    "error": "Validation Error",
                    "status_code": response.status_code,
                    "details": error_data,
                }

            if response.status_code == 401:
                raise RuntimeError("Wrong API key.")

            return {
                "success": False,
                "error": "HTTP Error",
                "status_code": response.status_code,
                "details": response.text,
            }
    except Exception as e:
        return {"success": False, "error": "Network or Internal Error", "details": str(e)}


@mcp.tool("forkflux_list_roles")
def list_roles():
    """
    Returns a list of available agent roles.

    Use this when you are a Source Agent preparing to publish a new job
    and need to know which roles (e.g., 'qa', 'refactorer', 'security')
    are available to handle specific types of tasks.
    """
    return _api_request("GET", "/agents/roles")


@mcp.tool("forkflux_create_job")
def create_job(
    summary: str,
    context_payload: dict[str, Any],
    target_role_key: str,
    constraints: list[str],
    artifacts: list[JobArtifact],
    priority: JobPriorityEnum,
    parent_job_id: int | None = None,
):
    """
    Publishes a new handoff job to the ForkFlux coordination bus for delegation.

    Use this tool when you (as a Source Agent) need to hand off a job to another
    specialized agent (Target Agent) on a different machine or environment.

    CRITICAL: The Target Agent operates in complete isolation. They cannot see your
    local workspace, files, or chat history. You MUST pack all necessary context
    into the parameters below.

    Args:
        summary: A concise, human-readable title of the job.
        context_payload: The complete isolated context required to execute the job.
            Include relevant code snippets, error logs, state descriptions, and steps to reproduce.
        target_role_key: The required specialization for this job. MUST be a valid key
            retrieved using the `list_roles` tool (e.g., 'qa_agent', 'security_reviewer').
        constraints: A list of strict acceptance criteria or execution boundaries the Target Agent must follow.
        artifacts: A list of external resources (like S3 URIs, Git commits, or database dumps) attached to this job.
        priority: The urgency of the job (10=LOW, 20=NORMAL, 30=HIGH, 40=URGENT).
        parent_job_id: (Optional) The ID of the job that spawned this job, used for tracing the handoff chain.
    """
    serialized_artifacts = [artifact.model_dump() for artifact in artifacts] if artifacts else []

    return _api_request(
        "POST",
        "/jobs",
        json_data={
            "summary": summary,
            "context_payload": context_payload,
            "target_role_key": target_role_key,
            "constraints": constraints,
            "artifacts": serialized_artifacts,
            "priority": priority,
            "parent_job_id": parent_job_id,
        },
    )


@mcp.tool("forkflux_list_jobs")
def list_jobs(
    limit: Annotated[int, Field(default=50, ge=1, le=200)] = 50,
    status: JobStatusEnum | None = JobStatusEnum.PUBLISHED,
    target_role_key: str | None = None,
    my_role_only: bool = True,
):
    """
    Fetches a list of jobs from the ForkFlux Coordination Bus.
    Target Agents should use this tool to poll the Shared Task Pool for available jobs to claim.

    Args:
        limit: The maximum number of jobs to return (min 1, max 200). Default is 50.
        status: Filter by task lifecycle status. Defaults to 'published' (jobs ready to be claimed).
        target_role_key: Filter jobs explicitly intended for a specific agent role.
        my_role_only: If True (default), filters the pool to return only jobs matching the current agent's role.

    Returns:
        A JSON response containing the list of jobs matching the filters.
    """

    return _api_request(
        "GET",
        "/jobs",
        params={
            "limit": limit,
            "status": status.value if status else None,
            "target_role_key": target_role_key,
            "my_role_only": my_role_only,
        },
    )


@mcp.tool("forkflux_job_details")
def get_job_details(job_id: Annotated[int, Field(description="The unique numeric ID of the job to retrieve.")]):
    """
    Fetches the detailed card and full handoff context for a specific job.

    Target Agents MUST use this tool to retrieve the complete 'context_payload',
    'constraints', and 'artifacts' needed to understand and execute the task.
    While 'forkflux_list_jobs' provides a summary, this tool provides the actual
    data payload required to do the work.

    Use this tool after finding a relevant job in the pool, or if a user provides a specific job ID.

    Args:
        job_id: The ID of the job.

    Returns:
        A JSON response containing the full job details, including metadata and execution context.
    """
    return _api_request("GET", f"/jobs/{job_id}")


@mcp.tool("forkflux_claim_job")
def claim_job(job_id: Annotated[int, Field(description="The unique ID of the job to claim.")]):
    """
    Atomically claims a published job from the ForkFlux coordination bus.

    Target Agents MUST call this tool immediately after deciding to take a job
    (usually found via 'forkflux_list_jobs'), BEFORE starting any actual execution.
    Claiming transitions the job status from 'published' to 'claimed' and
    assigns it to you, preventing other agents from taking it.

    If the claim fails (e.g., returns an HTTP 409 Conflict error), it means
    another agent has already claimed this job. In that case, do not proceed
    with the work; instead, fetch the list of jobs again to find a new one.

    Args:
        job_id: The ID of the job you want to lock and claim for yourself.

    Returns:
        JSON response confirming the successful claim, or an error message.
    """
    return _api_request("POST", f"/jobs/{job_id}/claim")


@mcp.tool("forkflux_change_job_status")
def change_job_status(
    job_id: Annotated[int, Field(description="The unique ID of the job.")],
    status: JobChangeStatusEnum,
    failure_reason: Annotated[
        str | None,
        Field(
            description="A detailed explanation of why the task failed. REQUIRED if status is 'failed', otherwise ignore."  # noqa: E501
        ),
    ] = None,
):
    """
    Updates the execution lifecycle status of a job you have claimed.

    Target Agents MUST use this tool to reflect their current progress to the Coordination Bus.
    Follow this state machine:
    1. 'in_progress': Set this IMMEDIATELY after claiming the job and before you start reading files or writing code.
    2. 'completed': Set this when you have successfully finished the task and met all acceptance criteria.
    3. 'failed': Set this if you cannot complete the task. CRITICAL: You MUST provide a detailed `failure_reason`
        (e.g., "missing context payload", "broken environment", "compilation error: <logs>")
        so the engineering team or Source Agent knows exactly what to fix.
    4. 'cancelled': Set this if the user explicitly asks you to drop the task.

    Args:
        job_id: The ID of the job you are updating.
        status: The new status to apply.
        failure_reason: The reason for failure.

    Returns:
        JSON response confirming the status update.
    """
    return _api_request(
        "POST", f"/jobs/{job_id}/status", json_data={"status": status.value, "failure_reason": failure_reason}
    )


if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=9000, docs_url="/docs")
