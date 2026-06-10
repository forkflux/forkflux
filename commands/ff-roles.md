---
description: List available ForkFlux roles by calling the MCP tool forkflux_list_roles.
---

# ff-roles

## Description

Lists all available target roles for ForkFlux handoff routing. These roles define who can claim the job on the receiving end. This is typically used to discover the correct `target_role_key` before publishing a task.

## Required MCP tool

`forkflux_list_roles`

## Agent instructions

CRITICAL RULE: DO NOT use bash, curl, or terminal commands to execute this API call. ALWAYS use the provided `forkflux_list_roles` MCP tool.

1. Call the `forkflux_list_roles` tool (no parameters required).
2. If the tool call fails, output the exact error message and stop. Do not hallucinate or guess role names.
3. If successful, parse the response and present the available roles to the user as a clean, human-readable Markdown list.
4. For each role, clearly highlight the `role_key` (using inline code formatting `like_this`) and provide its description.
5. **Tool Chaining Prompt:** End your response by naturally suggesting the next step. Remind the user that they can now use the `/ff-push` command to create a handoff job using one of these keys.

## Output

Provide a clear, high-visibility list in Markdown:

* 🎭 **Available Target Roles:**
  * `[role_key_1]` — Description of role 1.
  * `[role_key_2]` — Description of role 2.

* 💡 **Next Step:** A brief tip: "You can now use `/ff-push` to publish your work and assign it to one of these roles."

**Strict Rule:** Keep the user notification concise. Do not dump raw API JSON responses.
