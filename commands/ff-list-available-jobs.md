---
description: Fetch available published jobs strictly for the agent's current role from the ForkFlux shared pool using the forkflux_list_jobs MCP tool.
---

# ff-list-available-jobs

## Description

Fetches a list of published jobs from the ForkFlux coordination bus that are specifically available for the agent's current role. This is typically used by a Target Agent (Receiver) to automatically pull relevant work waiting in the queue without needing to specify roles manually.

## Required MCP tool

`forkflux_list_jobs`

## Agent instructions

1. Call the `forkflux_list_jobs` MCP tool with the exact following arguments:
   * `status`: "published"
   * `target_role_key`: null
   * `my_role_only`: true
2. Do not change these parameters. They are strictly required to filter only the tasks ready to be claimed by your specific role.
3. If the tool call fails or returns a connection error, output the exact error message and stop. Do not hallucinate or make up mock jobs.
4. If the returned list is empty, kindly inform the user that there are currently no published tasks available for your role in the shared pool.
5. If jobs are found, present them to the user as a clean, easily scannable Markdown table.
6. Conclude your response by asking the user which **Job ID** they would like you to claim (e.g., using `/ff-claim-job`).

## Output

Generate a human-readable Markdown table with the following columns:

* **Job ID**: (Rendered as inline code for easy copying)
* **Priority**: The execution priority (e.g., 10, 20, 30).
* **Source / Creator**: (If available) Who created the task.
* **Status**: Current lifecycle state (will always be `published`).
* **Summary**: A brief, truncated snippet of the `constraints` or acceptance criteria.

Ask the user to select a task to claim.

**Strict Rule:** Never dump raw JSON. Always parse the payload into the table format.
