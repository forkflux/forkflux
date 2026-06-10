---
description: Create a new handoff job in the ForkFlux Coordination Bus using the forkflux_create_job MCP tool.
---

# ff-create-job

## Description

Creates a new handoff job for a target agent to claim. This packages the current execution context, acceptance criteria, and relevant artifacts, and publishes them to the decentralized ForkFlux coordination bus.

## Required MCP tool

`forkflux_create_job`

## Agent instructions

1. Before calling the tool, verify that you have a valid `target_role_key`. If you do not know the exact key, stop and ask the user to run `/ff-list-roles` first. Do not guess or hallucinate the role key.
2. Prepare the parameters for the tool call carefully:
   - `target_role_key`: (String) The exact role key retrieved previously.
   - `constraints`: (String) Explicit acceptance criteria. Clearly state what the target agent must achieve to consider this handoff job complete.
   - `context_payload`: (JSON/Dictionary) A highly detailed, structured JSON object containing the context of the work you just finished, any implicit problems you tried to bypass, and what the next agent needs to know. Do not pass a simple, flat string.
   - `priority`: (Integer) Must be exactly 10, 20, 30, or 40 (if required).
   - `artifacts`: (Array) List of generated files/logs, if any. Each object must include `type`, `uri`, `checksum`, and `metadata_json`.
3. Call the `forkflux_create_job` tool.
4. If the tool call fails, output the exact error message and stop. Do not attempt to retry with fake data.
5. If successful, parse the response to extract the new Job ID and details.

## Output

Provide a clear, human-readable Markdown confirmation to the user.
Include:
- 🚀 **Job ID**: The ID of the newly created handoff job.
- 🎯 **Target Role**: The role that is supposed to pick this up.
- ✅ **Acceptance Criteria**: A brief summary of the constraints you passed.
Do not dump raw JSON output unless there was a specific error that the user needs to debug.
