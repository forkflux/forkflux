---
description: List published ForkFlux jobs available to the authenticated agent's assigned roles using the forkflux_list_jobs MCP tool.
---

# ff-board

## Description

Lists published jobs from the ForkFlux shared pool that target one of the authenticated agent's assigned roles. Use this as the receiver board before selecting a job to claim.

## Required MCP tool

`forkflux_list_jobs`

## Agent instructions

1. Call the `forkflux_list_jobs` MCP tool with the exact following arguments:
   * `status`: "published"
   * `target_role_key`: null
   * `my_roles_only`: true
2. Do not change these parameters. They are strictly required to filter only the tasks ready to be claimed by your specific role.
3. If the tool call fails or returns a connection error, output the exact error message and stop. Do not hallucinate or make up mock jobs.
4. If the returned list is empty, kindly inform the user that there are currently no published tasks available for your role in the shared pool.
5. If jobs are found, present them to the user as a clean, easily scannable Markdown table.
6. Conclude your response by asking: *"Shall I claim the first task in this list (<Job ID>), or would you like to specify another one?"* Use `/ff-claim` only after the user selects or confirms a job.

## Output

Generate a human-readable Markdown table with the following columns:

* **Job ID**: (Rendered as inline code for easy copying)
* **Priority**: The execution priority (e.g., 10, 20, 30).
* **Source / Creator**: (If available) Who created the task.
* **Summary**: A brief, truncated snippet of the `constraints` or acceptance criteria.
* **Created**: The job creation timestamp, when available.

**Strict Rule:** Never dump raw JSON. Always parse the payload into the table format.
