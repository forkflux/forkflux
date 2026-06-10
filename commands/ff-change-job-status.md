---
description: Update the execution lifecycle status of a specific ForkFlux job using the forkflux_change_job_status MCP tool.
---

# ff-change-job-status

## Description

Updates the lifecycle state of a specific ForkFlux job. This command advances the status tracker (e.g., moving from `claimed` to `in_progress`, or marking a job as `completed` or `failed`), broadcasting the progress across the entire decentralized coordination bus.

## Required MCP tool

`forkflux_change_job_status`

## Agent instructions

1. Before calling the tool, ensure you have a valid `job_id` and the explicit target `status`.
2. Validate that the target status matches one of the strictly allowed ForkFlux lifecycle states: `in_progress`, `completed`, `failed`, or `cancelled`.
3. Adhere to the strict lifecycle state transitions defined by the protocol. Do not bypass states:
   - `claimed` -> `in_progress` (Call this immediately when you start executing the code/tests)
   - `in_progress` -> `completed` (Call this ONLY after verifying that all acceptance criteria and constraints from the job card are fully met)
   - `in_progress` -> `failed` or `claimed` -> `failed` (Call this if an unrecoverable error occurs)
   - `published` -> `cancelled` or `claimed` -> `cancelled`
4. **Mandatory Failure Logging:** If you are changing the status to `failed`, you MUST populate the `failure_reason` parameter. Provide a detailed summary of the error, stack trace excerpts, or unmet constraints so human engineers can debug the handoff block.
5. Call the `forkflux_change_job_status` tool with the required arguments.
6. If the tool call fails (e.g., due to an invalid state transition or authorization error), output the exact error message and stop. Do not hallucinate a successful update.
7. Inform the user of the successful transition and suggest the next logical step (e.g., if `completed`, notify that the handoff pipeline for this job is closed).

## Output

Provide a clear, high-visibility status update block in Markdown:

* 🔄 **Job Status Updated**: Reference the `job_id`.
* 🚦 **Lifecycle State**: The new state (e.g., `in_progress`, `completed`, `failed`).
* 📝 **Context / Error Details**: If marked as `failed`, print the explicit `failure_reason`. Otherwise, write a brief sentence on what action triggered this transition.

**Strict Rule:** Keep the user notification concise. Do not dump raw API JSON responses unless an explicit tool execution failure occurs.
