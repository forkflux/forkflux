---
description: Update a specific ForkFlux job lifecycle status using the forkflux_change_job_status MCP tool.
---

# ff-close

## Description

Updates a specific ForkFlux job lifecycle status. This command can temporarily mark claimed work as `blocked`, resume eligible work as `in_progress`, or close work with a terminal state (`completed`, `failed`, or `cancelled`).

## Required MCP tool

`forkflux_change_job_status`

## Agent instructions

CRITICAL RULE: DO NOT use bash or terminal commands to execute this API call. ALWAYS use the provided `forkflux_change_job_status` MCP tool.

1. Before calling the tool, ensure you have a valid `job_id` from your current context and the explicit target `status`.
2. Validate that the target status is one of the allowed lifecycle states: `blocked`, `in_progress`, `completed`, `failed`, or `cancelled`. Use `in_progress` only to resume a previously `blocked` or `failed` job; do not use it for normal claiming.
3. Adhere to these strict validation rules before transitioning:
   - `completed`: Call this ONLY after verifying that all code is written, tests (if any) are passed, and all acceptance criteria from the job card are fully met.
   - `failed`: Call this if an unrecoverable error occurs, tests persistently fail, or constraints cannot be met.
   - `cancelled`: Call this if the user explicitly aborts the job.
   - `blocked`: Call this if the assignee cannot proceed temporarily due to an external dependency or environment issue. The assistant must include a useful `blocked_reason`. Use `in_progress` to unblock once the blocker is resolved.
4. **Mandatory Failure Logging:** If you are changing the status to `failed`, you MUST populate the `failure_reason` argument. Provide a detailed summary of the error, stack trace excerpts, or unmet constraints so human engineers can debug the handoff block.
5. **Mandatory Blocked Logging:** If you are changing the status to `blocked`, you MUST populate the `blocked_reason` argument with a useful explanation of what is missing and what would unblock progress.
6. Call the `forkflux_change_job_status` tool with the appropriate arguments.
7. If the tool call fails (e.g., due to an invalid state transition from the Coordination Bus), output the exact error message and stop. Do not hallucinate a successful update.
8. Upon successful transition, inform the user that the lifecycle status for this job was updated.

## Output

Provide a clear, high-visibility status update block in Markdown:

* 🔄 **Job Updated**: Reference the `job_id`.
* 🚦 **State**: The target state (`blocked`, `in_progress`, `completed`, `failed`, or `cancelled`).
* 📝 **Summary / Error Details**:
  - If `completed`: Write a brief 1-2 sentence summary of what was implemented to meet the acceptance criteria.
  - If `failed`: Print the explicit `failure_reason` provided to the tool.
  - If `blocked`: Print the explicit `blocked_reason` and what is needed to unblock.

**Strict Rule:** Keep the user notification concise and human-readable. Do not dump raw API JSON responses.
