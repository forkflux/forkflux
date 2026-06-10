---
description: Close a specific ForkFlux job by updating its lifecycle status to a terminal state (completed, failed, or cancelled) using the forkflux_change_job_status MCP tool.
---

# ff-close

## Description

Finalizes and closes a specific ForkFlux job. This command updates the status tracker to a terminal state (`completed`, `failed`, or `cancelled`), broadcasting the completion or failure across the decentralized coordination bus.

## Required MCP tool

`forkflux_change_job_status`

## Agent instructions

CRITICAL RULE: DO NOT use bash or terminal commands to execute this API call. ALWAYS use the provided `forkflux_change_job_status` MCP tool.

1. Before calling the tool, ensure you have a valid `job_id` from your current context and the explicit target `status`.
2. Validate that the target status is strictly one of the allowed TERMINAL lifecycle states: `completed`, `failed`, or `cancelled`. Do NOT use this command to transition to `in_progress`.
3. Adhere to these strict validation rules before transitioning:
   - `completed`: Call this ONLY after verifying that all code is written, tests (if any) are passed, and all acceptance criteria from the job card are fully met.
   - `failed`: Call this if an unrecoverable error occurs, tests persistently fail, or constraints cannot be met.
   - `cancelled`: Call this if the user explicitly aborts the job.
4. **Mandatory Failure Logging:** If you are changing the status to `failed`, you MUST populate the `failure_reason` argument. Provide a detailed summary of the error, stack trace excerpts, or unmet constraints so human engineers can debug the handoff block.
5. Call the `forkflux_change_job_status` tool with the appropriate arguments.
6. If the tool call fails (e.g., due to an invalid state transition from the Coordination Bus), output the exact error message and stop. Do not hallucinate a successful update.
7. Upon successful transition, inform the user that the handoff pipeline for this job is closed.

## Output

Provide a clear, high-visibility status update block in Markdown:

* 🔄 **Job Closed**: Reference the `job_id`.
* 🚦 **Final State**: The terminal state (`completed`, `failed`, or `cancelled`).
* 📝 **Summary / Error Details**:
  - If `completed`: Write a brief 1-2 sentence summary of what was implemented to meet the acceptance criteria.
  - If `failed`: Print the explicit `failure_reason` provided to the tool.

**Strict Rule:** Keep the user notification concise and human-readable. Do not dump raw API JSON responses.
