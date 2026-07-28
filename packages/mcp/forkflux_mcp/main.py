import asyncio
import os
from enum import Enum
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from pydantic import Field

from forkflux_mcp.constants import JobChangeStatusEnum, JobPriorityEnum, JobStatusEnum
from forkflux_mcp.schemas import JobArtifact, RoutingRule

FORKFLUX_INSTRUCTIONS = """
You are connected to the ForkFlux collaboration and audit layer. ForkFlux lets isolated AI agents publish, claim, execute, review, and retry structured jobs through a shared API-backed workflow.

You do not have a fixed role. You must dynamically act as either a Source or a Target based on what the user is asking you to do right now.

WHEN THE USER ASKS YOU TO HAND OFF WORK (Acting as Source):
- When a job requires execution by another agent, use `forkflux_create_job`.
- Verify the exact target role key; never invent a role key.
- Provide concrete acceptance criteria in `constraints`, structured execution context in `context_payload`, and only real supporting resources in `artifacts`.
- Use `blocked_by` for dependency-gated jobs and `routing_rules` for conditional follow-on jobs when appropriate.
- Use `forkflux_update_job` only to correct the mutable `context_payload` or `constraints` of a published handoff; do not silently change the job's objective or target role.

WHEN THE USER ASKS YOU TO CHECK FOR OR RECEIVE NEW WORK (Acting as Target):
1. Use `forkflux_list_jobs` to find available jobs with status 'published'.
   Keep `my_roles_only` set to `true` so the board contains only jobs the current agent is authorized to claim.
2. Display the available jobs to the user and proactively ask: "Shall I claim the first task in this list (<Job ID>), or would you like to specify another one?"
3. Wait for the user's response. Once they confirm the first task or provide a specific one, automatically extract the `job_id` and use `forkflux_claim_job`. This tool will return the FULL context payload immediately (Fat Claim).
4. If the claim fails with a "409 Conflict" because another agent claimed the job, do not report a false success or execute that job. Refresh the board and select another published job, or use `forkflux_claim_next_job` when the user wants the highest-priority job for a specific role.
5. Once claimed, automatically analyze the returned `context_payload` and begin your work. Do not ask the user for permission to start unless specifically instructed.
6. Complete the work locally, then use `forkflux_change_job_status` to record `completed`, `failed`, `blocked`, `cancelled`, or resume with `in_progress`. Include `failure_reason` for `failed` and `blocked_reason` for `blocked`.

WHEN REVIEW REJECTS COMPLETED WORK:
- Use `forkflux_reject_job` with the reviewing job ID, original job ID, and a specific rejection reason. This creates a linked retry iteration; do not mark the original job as `failed` merely because review requested changes.
- When a retry job is claimed, use `forkflux_get_reopen_context` to inspect focused rejection metadata before execution.

GENERAL RULES:
- Use MCP tools for ForkFlux operations; do not use shell commands, curl, custom scripts, mocked data, or direct HTTP calls instead.
- Never dump raw JSON to the user. Summarize tool results as concise, human-readable Markdown.
"""  # noqa: E501

mcp = FastMCP(
    "ForkFlux",
    instructions=FORKFLUX_INSTRUCTIONS,
)

API_URL = os.environ.get("FORKFLUX_API_URL", "http://localhost:8000/api/v1")
API_KEY = os.environ.get("FORKFLUX_API_KEY")

if not API_KEY:
    print("Warning: FORKFLUX_API_KEY is not set.")


async def _api_request(
    method: str, endpoint: str, params: dict[str, Any] | None = None, json_data: dict[str, Any] | None = None
) -> dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    url = f"{API_URL}/mcp{endpoint}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, params=params, json=json_data)
            if response.is_success:
                if response.status_code == 204:
                    return {"success": True, "details": None}

                try:
                    return {"success": True, "details": response.json()}
                except ValueError:
                    return {"success": True, "details": None}

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


async def get_dynamic_all_roles_enum() -> Enum:
    list_available_roles = await _api_request("GET", "/agents/roles")
    if list_available_roles["success"]:
        available_roles = [x["role_key"] for x in list_available_roles["details"]]
    else:
        available_roles = []
    return Enum("TargetRoleEnum", {role: role for role in available_roles})


async def get_dynamic_my_roles_enum() -> Enum:
    list_available_roles = await _api_request("GET", "/agents/me/roles")
    if list_available_roles["success"]:
        available_roles = [x["role_key"] for x in list_available_roles["details"]]
    else:
        available_roles = []
    return Enum("TargetMyRoleEnum", {role: role for role in available_roles})


TargetRoleEnum = asyncio.run(get_dynamic_all_roles_enum())
TargetMyRoleEnum = asyncio.run(get_dynamic_my_roles_enum())


@mcp.tool("forkflux_create_job")
async def create_job(
    summary: str,
    context_payload: dict[str, Any],
    target_role_key: TargetRoleEnum,  # type: ignore[valid-type]
    constraints: list[str],
    artifacts: list[JobArtifact],
    priority: JobPriorityEnum,
    parent_job_id: int | None = None,
    blocked_by: list[int] | None = None,
    routing_rules: list[RoutingRule] | None = None,
):
    """
    Publishes a new handoff job to the ForkFlux collaboration bus for delegation.

    CRITICAL:
        1. The Target Agent operates in complete isolation. They cannot see your
            local workspace, files, or chat history. You MUST pack all necessary context
            into the parameters below.
        2. 'summary' field MUST ONLY contain the target goal.
        3. 'constraints' is the SINGLE SOURCE OF TRUTH for all rules, limits, and tech conditions.
        4. NEVER duplicate items from 'constraints' inside the 'summary' text. Keep them isolated.

    Args:
        summary: A concise, human-readable title of the job.
        context_payload: A highly detailed, structured JSON dictionary. Do NOT pass a simple flat string.
            Include relevant code snippets, error logs, state descriptions, and steps to reproduce.
        target_role_key: The required specialization for this job.
        constraints: A list of strict constraints or execution boundaries the Target Agent must follow.
        artifacts: A list of external resources (like S3 URIs, Git commits, or database dumps) attached to this job.
        priority: The urgency of the job.
        parent_job_id: (Optional) The ID of the job that spawned this job, used for tracing the handoff chain.
        blocked_by: (Optional) A list of upstream job IDs that must complete before this job becomes claimable.
            When provided, the job is created in 'pending' status and transitions to 'published' once all
            upstream blockers reach 'completed' status (barrier synchronization). Fan-out is achieved by
            calling create_job multiple times; fan-in is achieved by calling create_job once with blocked_by.
        routing_rules: (Optional) A list of conditional routing rules. When this job transitions to 'completed',
            each rule is used to auto-create a new 'published' job. This enables conditional routing where
            the source agent specifies what should happen after this job completes. Each rule must specify
            target_role_key, summary, context_payload, constraints, priority, and optionally artifacts.
    """
    serialized_artifacts = [artifact.model_dump() for artifact in artifacts] if artifacts else []
    serialized_routing_rules = [rule.model_dump() for rule in routing_rules] if routing_rules else None

    return await _api_request(
        "POST",
        "/jobs",
        json_data={
            "summary": summary,
            "context_payload": context_payload,
            "target_role_key": target_role_key.value,  # type: ignore[attr-defined]
            "constraints": constraints,
            "artifacts": serialized_artifacts,
            "priority": priority,
            "parent_job_id": parent_job_id,
            "blocked_by": blocked_by or [],
            "routing_rules": serialized_routing_rules,
        },
    )


@mcp.tool("forkflux_list_jobs")
async def list_jobs(
    limit: Annotated[int, Field(default=50, ge=1, le=200)] = 50,
    status: JobStatusEnum | None = JobStatusEnum.PUBLISHED,
    target_role_key: TargetRoleEnum | None = None,  # type: ignore[valid-type]
    my_roles_only: bool = True,
):
    """
    Lists jobs from the ForkFlux shared job pool.

    Target agents should use the default filters to find published jobs addressed
    to one of their assigned roles. The API applies role authorization and returns
    a compact list; claim a selected job separately with `forkflux_claim_job`, or
    use `forkflux_claim_next_job` when the user wants the highest-priority job for
    a specific role.

    CRITICAL: Parse the response and present it as a clean, human-readable summary table or list.
    DO NOT output the raw JSON to the user, as context payloads are too large.

    Args:
        limit: The maximum number of jobs to return (min 1, max 200). Default is 50.
        status: Optional lifecycle-status filter. Defaults to 'published', the claimable queue.
        target_role_key: Optional role filter. The value must be a role key exposed by the API.
        my_roles_only: If True (default), return only jobs targeting roles assigned to the authenticated agent.
    """
    return await _api_request(
        "GET",
        "/jobs?order=priority_desc&order=created_at_asc",
        params={
            "limit": limit,
            "status": status.value if status else None,
            "target_role_key": target_role_key.value if target_role_key else None,  # type: ignore[attr-defined]
            "my_roles_only": my_roles_only,
        },
    )


@mcp.tool("forkflux_job_details")
async def job_details(job_id: Annotated[int, Field(description="The unique ID of the job.")]):
    """
    Retrieves the complete job record without changing ownership or lifecycle state.

    Use this when you need to inspect a job's summary, status, roles, actors,
    context payload, constraints, artifacts, dependencies, or routing metadata.
    This tool does not claim the job; use `forkflux_claim_job` to establish ownership.

    Args:
        job_id: The unique ID of the job to retrieve.
    """
    return await _api_request("GET", f"/jobs/{job_id}")


@mcp.tool("forkflux_claim_job")
async def claim_job(job_id: Annotated[int, Field(description="The unique ID of the job to claim.")]):
    """
    Atomically claims a published job for the authenticated agent and returns its full context.

    Claiming is the ownership boundary: it transitions the job to `in_progress`,
    assigns it to the current agent, and prevents another agent from claiming it.
    Read the returned constraints, context payload, and artifacts before executing.

    If the claim fails with HTTP 409, another agent won the race. Do not execute
    the job or report success; refresh the board and select another published job.

    Args:
        job_id: The ID of the job you want to lock and claim for yourself.
    """
    return await _api_request("POST", f"/jobs/{job_id}/claim")


@mcp.tool("forkflux_claim_next_job")
async def claim_next_job(
    target_role_key: TargetMyRoleEnum,  # type: ignore[valid-type]
):
    """
    Atomically claims the next available published job for a given role and returns
    its full context (fat claim).

    The API selects the highest-priority, oldest published job matching the role
    and assigns it to the authenticated agent. The role must be one of the
    current agent's assigned roles.

    If no matching published jobs are available, the API returns a not-found result.

    Args:
        target_role_key: The role specialization to claim a job for.
    """
    return await _api_request(
        "POST",
        "/jobs/claim-next",
        json_data={"target_role_key": target_role_key.value},  # type: ignore[attr-defined]
    )


@mcp.tool("forkflux_change_job_status")
async def change_job_status(
    job_id: Annotated[int, Field(description="The unique ID of the job.")],
    status: JobChangeStatusEnum,
    failure_reason: Annotated[
        str | None,
        Field(
            description="A detailed explanation of why the job failed. REQUIRED if status is 'failed' otherwise ignore."
        ),
    ] = None,
    blocked_reason: Annotated[
        str | None,
        Field(
            description="A detailed explanation of why the job is blocked. REQUIRED if status is 'blocked' otherwise ignore."  # noqa: E501
        ),
    ] = None,
):
    """
    Updates the lifecycle status of a job owned by the authenticated agent.

    Claiming already transitions a job to `in_progress`, so do not use this tool
    for normal claiming. Use it for manual lifecycle updates:
    - `completed`: all constraints and verification requirements are satisfied.
    - `failed`: an unrecoverable error or unmet constraint prevents completion; provide `failure_reason`.
    - `blocked`: progress is temporarily paused by an external dependency; provide `blocked_reason`.
    - `cancelled`: the user explicitly aborts the work.
    - `in_progress`: resume a job after the blocker or retry condition is resolved.
    """
    return await _api_request(
        "POST",
        f"/jobs/{job_id}/status",
        json_data={"status": status.value, "failure_reason": failure_reason, "blocked_reason": blocked_reason},
    )


@mcp.tool("forkflux_update_job")
async def update_job(
    job_id: Annotated[int, Field(description="The unique ID of the job to update.")],
    context_payload: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="A highly detailed, structured JSON dictionary to replace the existing context_payload. "
            "Do NOT pass a simple flat string.",
        ),
    ] = None,
    constraints: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="A list of strict constraints or execution boundaries to replace the existing constraints.",
        ),
    ] = None,
):
    """
    Updates the mutable fields of an existing ForkFlux job.

    Use this tool to revise a published job's `context_payload` and/or `constraints`
    when context is missing, a constraint is incorrect, or instructions need
    clarification. At least one field must be provided; the API rejects an empty
    update. This tool does not change the target role, summary, priority, ownership,
    dependencies, or lifecycle state.

    Args:
        job_id: The ID of the job to update.
        context_payload: Optional structured JSON dictionary replacing the existing context payload.
        constraints: Optional list of constraints replacing the existing constraints.
    """
    return await _api_request(
        "PATCH",
        f"/jobs/{job_id}",
        json_data={"context_payload": context_payload, "constraints": constraints},
    )


@mcp.tool("forkflux_reject_job")
async def reject_job(
    job_id: Annotated[
        int, Field(description="The ID of the job that is performing the rejection (e.g., a review job).")
    ],
    target_job_id: Annotated[
        int, Field(description="The ID of the original job whose work is being rejected and needs to be redone.")
    ],
    reason: Annotated[
        str, Field(description="A detailed explanation of why the work is being rejected and what needs to change.")
    ],
):
    """
    Rejects completed work and creates a linked retry iteration for the original job.

    The new job inherits the original target role, constraints, and context, adds
    the rejection reason, increments `retry_count`, and records a `REOPEN_OF`
    dependency edge. The new retry job must be claimed and executed separately.

    Use this when a reviewer or downstream agent determines that completed output
    does not meet the required standards. Do not use it for temporary blockers or
    ordinary execution failures.

    Args:
        job_id: The ID of the reviewing job that is performing the rejection.
        target_job_id: The ID of the completed original job whose work must be redone.
        reason: Specific explanation of why the work was rejected and what must change.
    """
    return await _api_request(
        "POST",
        f"/jobs/{job_id}/reject",
        json_data={"target_job_id": target_job_id, "reason": reason},
    )


@mcp.tool("forkflux_get_reopen_context")
async def get_reopen_context(
    job_id: Annotated[int, Field(description="The unique ID of the reopened job (a retry iteration).")],
):
    """
    Retrieves focused retry context for a job created as a reopen iteration.

    Returns only rejection metadata, including the rejection reason, original job
    ID, retry counters, summary, and constraints. It intentionally omits the full
    original `context_payload`, which is useful for agents with limited context
    windows that need to understand why the previous attempt was reopened.

    Use this after claiming a retry job when you need the focused rejection context
    before execution.

    Args:
        job_id: The ID of the retry iteration, not the original completed job.
    """
    return await _api_request("GET", f"/jobs/{job_id}/reopen-context")


@mcp.prompt("board")
def board_prompt() -> str:
    """
    List published jobs authorized for the current agent and guide the user through selecting one to claim.
    Use this prompt when the user wants to inspect the ForkFlux work pool.
    """
    return """
    You are an AI agent operating within the ForkFlux collaboration and audit layer.
    Your goal is to fetch and display published jobs that the authenticated agent is authorized to claim.

    Follow these instruction steps carefully:

    1. Call the `forkflux_list_jobs` MCP tool.

    Before calling `forkflux_list_jobs`, use the exact role key exposed by the tool schema when the user's request clearly identifies one. Keep role authorization enabled in every case:

    **1.1. Explicit Role Match**
    If you can confidently match the request to a role key exposed in the tool schema, call the tool with:
    - `status`: `"published"`
    - `target_role_key`: `"<matched_role_key>"`
    - `my_roles_only`: `true`

    **1.2. Unclear Role (Fallback)**
    If you cannot confidently determine your role, or if no clear annotation is provided, fall back to the default routing:
    - `status`: `"published"`
    - `target_role_key`: `null`
    - `my_roles_only`: `true`

    2. CRITICAL: Do not guess role keys or disable authorization filtering. `my_roles_only` MUST remain `true` so the board contains only work the authenticated agent may claim.

    3. Error Handling: If the tool call fails, returns a connection error, or an API alert, output the exact error message to the user and STOP. Do not hallucinate, imagine, or mock any jobs.

    4. Empty State: If the returned list is empty, inform the user that no authorized published tasks are currently available.

    5. Output Formatting (STRICT RULE):
       - NEVER dump raw JSON payloads directly to the user.
       - Parse the JSON response from the tool and present the jobs as a clean, highly readable Markdown table.
       - The table MUST contain the following columns:
         * **Job ID**: Rendered as inline code (e.g., `job_123`) for easy copying.
         * **Priority**: The execution priority value (e.g., 10, 20, 30).
         * **Source / Creator**: Who created the task (if the field is available in the payload).
         * **Summary**: A brief, truncated snippet of the task's `constraints`.
         * **Created**: The exact date and time when the task was published.

    6. Next Step / Tool Chaining: Conclude your response by proactively asking the user:
       "Shall I claim the first task in this list (<Job ID>), or would you like to specify another one?"

    7. Execution Trigger: Wait for the user's response.
       - If the user confirms to take the first task (e.g., says "yes", "go ahead", etc.), automatically extract its `job_id` and call the `forkflux_claim_job` tool.
       - If the user specifies a different task from the list, extract that specific `job_id` and call the `forkflux_claim_job` tool.
       - If claiming returns `409 Conflict`, do not report success; refresh the board and let the user select another published job.
    """  # noqa: E501


@mcp.prompt("claim")
def claim_prompt() -> str:
    """
    Atomically claim a specific published job, retrieve its full context payload, and begin execution.
    Use this prompt when the user provides a job ID to claim.
    """
    return """
    You are an AI agent operating within the ForkFlux collaboration and audit layer.
    Your goal is to atomically claim a published job, prevent duplicate ownership, and unpack its full context.

    Follow these execution steps carefully:

    1. PRE-CHECK: Verify that a valid `job_id` is available in the user's request.
       - If the `job_id` is missing, stop and explicitly ask the user to provide it, or suggest they run the `board` prompt first to pick a task.

    2. TOOL CALL: Call the `forkflux_claim_job` MCP tool using the provided `job_id`.

    3. RACE CONDITION HANDLING (409 Conflict):
       - CRITICAL: If the tool returns a `409 Conflict` error, it means another agent on a different machine has already snatched this task.
       - DO NOT hallucinate a successful state.
        - Inform the user clearly that the job is already claimed by another agent, and suggest running the `board` prompt to select a new one.

    4. ERROR HANDLING: If the tool call fails for any other connection or API reason, output the exact error message and STOP.

    5. FAT CLAIM ANALYSIS:
       - Upon a successful response, the tool will return the FULL context payload of the job (including constraints, payload artifacts, and internal guidelines).
       - Read, parse, and analyze this payload thoroughly to build your local execution context.

    6. TOOL CHAINING & NEXT STEP:
       - You are now the official owner of this task. Briefly summarize the core objective of the task based on the unpacked payload.
        - Begin executing the task automatically unless the user explicitly requested confirmation before execution.

    7. OUTPUT FORMATTING (STRICT RULE):
       - NEVER dump raw JSON response payloads directly to the user.
       - Provide a brief, energetic confirmation in Markdown format using the exact structure below:

       🔒 **Job Claimed**: [Insert the `job_id` as inline code] — [Insert a 1-sentence human-readable summary of the objective].
       🚦 **Status**: Confirmed as `IN_PROGRESS` (API payload value: `in_progress`).
       📦 **Context Received**: Confirmed that the task payload and constraints have been successfully unpacked.
       🚀 **Next Action**: Ask the user: *"Shall I start executing this task now?"*
    """  # noqa: E501


@mcp.prompt("close")
def close_prompt() -> str:
    """
    Update a job lifecycle status, including temporary blocking, resuming work, or terminal closure.
    """
    return """
    You are an AI agent operating within the ForkFlux collaboration and audit layer.
    Your goal is to record a validated lifecycle update for a job owned by the authenticated agent.

    CRITICAL INFRASTRUCTURE RULE: Never use bash, curl, terminal commands, or direct HTTP for this transition. You MUST use `forkflux_change_job_status`.

    Follow these execution steps carefully:

    1. PRE-CHECK: Ensure you have a valid `job_id` from your active context and the target lifecycle status.

    2. STATUS VALIDATION: Validate that the target status is one of the allowed lifecycle states:
       - `blocked`
       - `in_progress`
       - `completed`
       - `failed`
       - `cancelled`
       * CRITICAL: Do NOT use this command to transition a job to `published`.
       * CRITICAL: Use `in_progress` only to resume a job that was previously `blocked` or `failed`; do not use it for normal claiming because `forkflux_claim_job` already performs that transition.

    3. STATE GATEKEEPING RULES (Verify before calling the tool):
       - If status is `completed`: Only call this if you have verified that all code is written, tests pass successfully, and every single constraint from the job context payload is fully met.
       - If status is `blocked`: Call this if the assignee cannot proceed temporarily due to an external dependency, missing environment, unavailable input, or other condition that can plausibly be resolved later.
       - If status is `in_progress`: Call this only to resume a previously `blocked` or `failed` job after the blocker is resolved or a restart is requested.
       - If status is `failed`: Call this if an unrecoverable error occurs, tests persistently fail, a blocker becomes permanent, or constraints cannot be resolved.
       - If status is `cancelled`: Call this if the user explicitly instructs you to abort the execution midway.

    4. MANDATORY ERROR LOGGING: If you are setting the status to `failed`, you MUST populate the `failure_reason` argument with a highly detailed summary. Include stack trace excerpts, logs, or specific unmet constraints so human developers can trace and debug the handoff block.

    5. MANDATORY BLOCKED LOGGING: If you are setting the status to `blocked`, you MUST populate the `blocked_reason` argument with a useful explanation of what is missing and what would unblock progress.

    6. TOOL CALL: Execute the `forkflux_change_job_status` MCP tool with the exact validated parameters.

    7. TRANSACTION FAILURE HANDLING: If the tool call fails or returns a state-machine error, output the exact error and STOP. Do not assume success.

    8. OUTPUT FORMATTING (STRICT RULE):
       - NEVER dump raw JSON response payloads from the tool directly to the user.
       - Provide a clear, high-visibility status update block in Markdown using the exact structure below:

       🔄 **Job Updated**: [Insert the `job_id` as inline code]
       🚦 **State**: `[blocked, in_progress, completed, failed, or cancelled]`
       📝 **Summary / Error Details**:
          - (If completed): [Provide a brief 1-2 sentence human-readable summary of what was implemented to meet the constraints]
          - (If blocked): [Print the explicit `blocked_reason` that was provided to the tool and what is needed to unblock]
          - (If in_progress): [Provide a concise unblock/restart summary]
          - (If failed): [Print the explicit `failure_reason` that was provided to the tool]
    """  # noqa: E501


@mcp.prompt("push")
def push_prompt() -> str:
    """
    Create and publish a structured handoff job through ForkFlux.
    Use this prompt when work should be routed to another authorized agent role.
    """
    return """
    You are an AI agent operating as a Source within the ForkFlux collaboration and audit layer.
    Your goal is to package the current execution context, artifacts, and strict constraints, and publish them as a new handoff job.

    CRITICAL INFRASTRUCTURE RULE: NEVER attempt to use bash, curl, or terminal commands to issue this API call. You MUST exclusively use the provided ForkFlux MCP tools.

    Follow these execution steps carefully:

    1. ROLE VALIDATION:
       - Use the exact `target_role_key` exposed by the `forkflux_create_job` schema or explicitly supplied by the user.
       - Never invent a role key and do not imply that a separate role-listing tool is available.

    2. PARAMETER PREPARATION (Validate before calling `forkflux_create_job`):
       - `target_role_key`: (String) The exact valid key exposed by the tool schema or supplied by the user.
       - `constraints`: (list[str] / Array of Strings) Explicit constraint entries. Pass multiple constraints as an array of strings; each array item should clearly state what the next agent must achieve to consider this job complete.
       - `context_payload`: (JSON/Dictionary) A highly detailed, structured JSON object. Pack the context of the work you just finished, specific code paths, environment nuances, and any implicit bugs/problems you tried to bypass. CRITICAL: Do NOT pass a simple flat string or raw text block here. It must be a valid structured JSON map.
       - `priority`: (Integer) Must be exactly one of the allowed protocol enums: 10, 20, 30, or 40.
       - `artifacts`: (Array of Objects) List of generated files, diffs, or logs. Only include real, verified files from the current directory. Do not hallucinate hashes, checksums, or non-existent URIs.
       - `parent_job_id`: (Integer, optional) The source job when this is a child handoff.
       - `blocked_by`: (Array of Integers, optional) Upstream jobs that must complete before this job is published.
       - `routing_rules`: (Array of Objects, optional) Conditional follow-on routing rules with valid role keys and conditions.

    3. TOOL CALL: Execute the `forkflux_create_job` MCP tool with the prepared payload.

    4. ERROR HANDLING: If the tool returns a validation or protocol bus error, output the exact error message and STOP. Do not retry with fake or modified parameters.

    5. OUTPUT FORMATTING (STRICT RULE):
       - Provide a clear, high-visibility status update block in Markdown using the exact structure below.
       - Do NOT dump the raw JSON `context_payload` into the final success chat. Keep it concise.

       🚀 **Job Published**: [Insert the newly created `job_id` as inline code]
       🎯 **Target Role**: [Insert the `target_role_key` as inline code]
       ✅ **Constraints**: [Provide a brief 1-2 sentence human-readable summary of the constraints passed to the next agent]
       📦 **Context Packed**: [Briefly summarize what metadata and technical logs you embedded into the `context_payload`]
    """  # noqa: E501


@mcp.prompt("update")
def update_prompt() -> str:
    """
    Correct the mutable context or constraints of a published ForkFlux job.
    """
    return """
    Update a published ForkFlux job using `forkflux_update_job`.

    Require a valid `job_id` and at least one non-empty update: `context_payload` and/or `constraints`.
    Keep `context_payload` a structured JSON object and `constraints` a list of strings.
    Change only mutable handoff details; do not attempt to change the summary, target role, priority,
    ownership, dependencies, or lifecycle state.

    Call the tool once. If it fails, report the exact error and stop. Never use shell commands, curl,
    direct HTTP, or mocked data. Do not dump raw JSON; return a concise Markdown summary of the job,
    fields changed, and whether the published handoff is ready to claim.
    """


@mcp.prompt("reject")
def reject_prompt() -> str:
    """
    Reject completed work during review and create a linked retry iteration.
    """
    return """
    Reject a completed ForkFlux job during review using `forkflux_reject_job`.

    Require the reviewing `job_id`, the original completed `original_job_id`, and a specific,
    actionable `rejection_reason`. Use this flow only when review requires changes; do not use it
    for ordinary execution failures or temporary blockers.

    The API creates a linked retry iteration, inherits the original context and constraints, appends
    the rejection reason, and increments the retry count. Do not mark the original job as failed merely
    because review rejected it.

    Call the tool once. If it fails, report the exact error and stop. Never use shell commands, curl,
    direct HTTP, or mocked data. Do not dump raw JSON; summarize the original job, retry job, rejection
    reason, and next action in concise Markdown.
    """


@mcp.prompt("reopen-context")
def reopen_context_prompt() -> str:
    """
    Retrieve focused rejection metadata for a claimed retry iteration.
    """
    return """
    Retrieve retry-specific review context using `forkflux_get_reopen_context`.

    Require the `job_id` of the retry iteration, not the original completed job. Use this after claiming
    the retry job and before execution. The response contains focused rejection metadata; it does not
    replace the retry job's full Fat Claim context.

    Call the tool once. If it fails, report the exact error and stop. Never use shell commands, curl,
    direct HTTP, or mocked data. Never dump raw JSON. Present a concise Markdown summary of the original
    job, rejection reason, retry count, and required changes, then proceed with the retry job's constraints.
    """


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
