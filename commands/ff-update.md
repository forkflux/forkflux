---
description: Correct the mutable context or constraints of a published ForkFlux job using the forkflux_update_job MCP tool.
---

# ff-update

## Description

Updates a published job's `context_payload` and/or `constraints` when the handoff needs clarification or correction. It does not change the job's summary, target role, priority, ownership, dependencies, or lifecycle state.

## Required MCP tool

`forkflux_update_job`

## Agent instructions

1. Verify a valid `job_id` and identify at least one field to replace.
2. Pass `context_payload` as a structured JSON object, not a flat string.
3. Pass `constraints` as an array of concrete acceptance criteria when updating them.
4. Do not use this command to change the target role, objective, priority, ownership, or status.
5. Call `forkflux_update_job` with the validated arguments.
6. If the tool fails, report the exact error and stop.

## Output

Report the updated `job_id`, the fields changed, and a concise summary. Do not dump raw JSON.
