---
description: Create a new handoff job in the ForkFlux Coordination Bus using the forkflux_create_job MCP tool.
---

# ff-push

## Description

Creates a new handoff job for a target agent to claim. This packages the current execution context, acceptance criteria, and relevant artifacts, and publishes them to the decentralized ForkFlux coordination bus.

## Required MCP tools

`forkflux_create_job`

## Agent instructions

CRITICAL RULE: DO NOT use bash, curl, or terminal commands to execute this API call. ALWAYS use the provided ForkFlux MCP tools.

1. **Tool Chaining (Role Discovery):** Before calling the creation tool, analyze available target role keys, select the correct one based on the user's intent, and proceed. Do not guess or hallucinate the role key.
2. Prepare the parameters for the `forkflux_create_job` call carefully:
   - `target_role_key`: (String) The exact valid role key retrieved.
   - `constraints`: (String) Explicit acceptance criteria. Clearly state what the target agent must achieve to consider this handoff job complete.
   - `context_payload`: (JSON/Dictionary) A highly detailed, structured JSON object containing the context of the work you just finished, any implicit problems you tried to bypass, and what the next agent needs to know. Do not pass a simple, flat string. This is the core of the cross-device handoff.
   - `priority`: (Integer) Must be exactly one of the allowed enum values: 10, 20, 30, or 40.
   - `artifacts`: (Array) List of generated files/logs, if any. Only include real, existing files. Do not hallucinate checksums or URIs.
3. Call the `forkflux_create_job` tool.
4. If the tool call fails (e.g., validation error), output the exact error message and stop. Do not attempt to retry with fake data.
5. If successful, parse the response to extract the new Job ID and details.

## Output

Provide a clear, high-visibility status update block in Markdown:

* 🚀 **Job Published**: Reference the new `job_id`.
* 🎯 **Target Role**: The `target_role_key` assigned to this job.
* ✅ **Constraints**: A brief 1-2 sentence summary of the constraints you passed to the next agent.
* 📦 **Context Packed**: Briefly mention what key information was packed into the `context_payload` (e.g., "Included test logs and modified file paths").

**Strict Rule:** Keep the user notification concise. Do not dump the raw JSON `context_payload` into the chat unless there was an explicit error that the user needs to debug.
