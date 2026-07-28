---
description: Reject completed ForkFlux work and create a linked retry job using the forkflux_reject_job MCP tool.
---

# ff-reject

## Description

Rejects completed work when review or QA finds that the original acceptance criteria were not met. The API creates a linked retry iteration with the rejection reason and incremented retry count.

## Required MCP tool

`forkflux_reject_job`

## Agent instructions

1. Verify the reviewing `job_id`, the original `target_job_id`, and a specific `reason`.
2. Use this command for review-driven rework, not temporary blockers or ordinary execution failures.
3. Call `forkflux_reject_job` with the validated arguments.
4. If the tool fails, report the exact error and stop.

## Output

Report the new retry `job_id`, original job ID, and retry count. Do not dump raw JSON.
