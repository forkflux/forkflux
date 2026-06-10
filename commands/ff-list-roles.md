---
description: List available ForkFlux roles by calling the MCP tool forkflux_list_roles.
---

## Description

Lists all available target roles for ForkFlux handoff routing. These roles define who can claim the job on the receiving end.

## Required MCP tool

`forkflux_list_roles`

## Agent instructions

1. Call the `forkflux_list_roles` tool (no parameters required).
2. If the tool call fails, output the exact error message and stop.
3. If successful, parse the response and present the available roles to the user as a clean Markdown list.
4. For each role, clearly highlight the role key (e.g., as bold or inline code) and its description.
5. End your response with a brief reminder that the chosen role key must be passed as the `target_role_key` when creating a new handoff job.

## Output

A formatted markdown list of roles with their keys and descriptions, followed by a short tip on next steps. Do not dump raw JSON unless explicitly asked.
