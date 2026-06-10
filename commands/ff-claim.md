---
description: Atomically claim a job from the ForkFlux coordination bus, retrieve its full context, and prepare for execution.
---

# ff-claim

## Description

Atomically claims a specific ForkFlux job, locking it for the current Target Agent and changing its status from `PUBLISHED` to `IN_PROGRESS` (API payload value: `in_progress`). This prevents race conditions where multiple agents might accidentally start working on the same job. It also returns the full job context in the claim response (Fat Claim) so the agent can immediately analyze the acceptance criteria and begin work.

## Required MCP tool

`forkflux_claim_job`

## Agent instructions

1. Before calling the tool, verify that the user has provided a valid `job_id`. If it is missing, ask the user for it or suggest running `/ff-list-available-jobs`.
2. Call the `forkflux_claim_job` tool using the provided `job_id`.
3. **Handle Race Conditions (409 Conflict):** If the tool returns a 409 Conflict error, it means another agent on a different machine has already claimed this job. Do NOT hallucinate a success. Kindly inform the user that the job was snatched by someone else, and suggest running `/ff-list-available-jobs` to pick a new one.
4. If the tool call fails for any other reason, output the exact error message and stop.
5. **Analyze Context (Fat Claim):** If successful, the tool response will contain the full context of the job (Acceptance Criteria, payload artifacts, instructions). Read and analyze this payload thoroughly.
6. **Next Logical Step (Tool Chaining):** You are now the official owner of this job. Briefly summarize the core objective based on the payload you just received.
7. Ask the user for confirmation to begin executing the work. **Crucial rule:** Remind yourself (and the user) that claiming already set the job to `IN_PROGRESS` (API payload value: `in_progress`), so proceed directly with execution.

## Output

Provide a brief, energetic confirmation to the user in Markdown format:

* 🔒 **Job Claimed**: Mention the `job_id` and a 1-sentence summary of the objective.
* 🚦 **Status**: Confirmed as `IN_PROGRESS` (API payload value: `in_progress`).
* 📦 **Context Received**: Confirm that you have successfully unpacked the task payload.
* 🚀 **Next Action**: Ask the user: *"Shall I start executing this task now?"*

**Strict Rule:** Do not dump raw JSON. Focus on the workflow transition and human-readable summary.
