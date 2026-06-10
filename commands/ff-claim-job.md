---
description: Atomically claim a job from the ForkFlux coordination bus using the forkflux_claim_job MCP tool.
---

# ff-claim-job

## Description

Atomically claims a specific ForkFlux job, locking it for the current Target Agent and changing its status from `published` to `claimed`. This prevents race conditions where multiple agents might accidentally start working on the same job.

## Required MCP tool

`forkflux_claim_job`

## Agent instructions

1. Before calling the tool, verify that the user has provided a valid `job_id`. If it is missing, ask the user for it or suggest running `/ff-list-jobs`.
2. Call the `forkflux_claim_job` tool using the provided `job_id`.
3. **Handle Race Conditions (409 Conflict):** If the tool returns a 409 Conflict error, it means another agent on a different machine has already claimed this job. Do NOT hallucinate a success. Kindly inform the user that the job was snatched by someone else, and suggest running `/ff-list-jobs` to pick a new one.
4. If the tool call fails for any other reason, output the exact error message and stop.
5. If successful, verify that the job status is now updated to `claimed`.
6. **Next Logical Step:** Once claimed, you are now the official owner of this job. Briefly remind the user of the core objective (based on your context memory from `/ff-job-details`) and ask for confirmation to begin executing the work.

## Output

Provide a brief, energetic confirmation to the user in Markdown format:

* 🔒 **Job Claimed**: Mention the `job_id`.
* 🚦 **Status**: Confirmed as `claimed`.
* 🚀 **Next Action**: Ask the user: *"Shall I start working on this now?"*

**Strict Rule:** Do not dump raw JSON. Focus on the workflow transition.
