---
description: Fetch available handoff jobs from the ForkFlux shared pool using the forkflux_list_jobs MCP tool.
---

# ff-list-jobs

## Description

Fetches a list of jobs from the ForkFlux coordination bus. This is typically used by a Target Agent (Receiver) to find available work that has been published by other agents across isolated environments.

## Required MCP tool

`forkflux_list_jobs`

## Agent instructions

1. Prepare the parameters for the tool call. Unless the user explicitly asks for a different status (e.g., checking failed or completed jobs), you must set the `status` parameter to `published`. This ensures you only retrieve jobs that are ready to be claimed.
2. Optional parameters you can configure based on user prompts:
   * `status`: (String) `published`, `claimed`, `in_progress`, `completed`, `failed`, or `cancelled`.
   * `limit`: (Integer) Maximum number of jobs to return.
3. Call the `forkflux_list_jobs` tool.
4. If the tool call fails or returns a connection error, output the exact error message and stop. Do not hallucinate or make up mock jobs.
5. If the returned list is empty, kindly inform the user that there are currently no jobs matching the criteria in the shared pool.
6. If jobs are found, present them to the user as a clean, easily scannable Markdown table.
7. Conclude your response by asking the user which **Job ID** they would like you to claim and start working on.

## Output

Generate a human-readable Markdown table with the following columns:

* **Job ID**: (Rendered as inline code for easy copying)
* **Target Role**: The role required to execute the job.
* **Priority**: The execution priority (e.g., 10, 20, 30).
* **Status**: Current lifecycle state.
* **Summary**: A brief, truncated snippet of the `constraints` or acceptance criteria.

Ask the user to select a task to claim.

**Strict Rule:** Never dump raw JSON. Always parse the payload into the table format.
