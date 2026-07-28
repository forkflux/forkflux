---
description: Retrieve focused rejection context for a ForkFlux retry job using the forkflux_get_reopen_context MCP tool.
---

# ff-reopen-context

## Description

Retrieves focused metadata for a retry iteration, including the rejection reason, original job ID, retry counters, summary, and constraints. It intentionally avoids returning the original full context payload.

## Required MCP tool

`forkflux_get_reopen_context`

## Agent instructions

1. Verify the supplied `job_id` identifies a retry iteration, not the original completed job.
2. Call `forkflux_get_reopen_context` with the job ID.
3. Use the returned rejection metadata to prepare the retry execution.
4. If the tool fails, report the exact error and stop.

## Output

Summarize the rejection reason, original job ID, retry count, and constraints. Do not dump raw JSON.
