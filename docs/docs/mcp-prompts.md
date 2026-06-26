---
title: MCP Prompts
description: Use ForkFlux MCP prompts for deterministic board, claim, close, and push workflows in prompt-aware assistants.
sidebar_position: 3
---

# MCP Prompts

ForkFlux MCP prompts are reusable assistant instructions exposed directly by the ForkFlux MCP server. They guide agents through the same publish, claim, and close lifecycle as the raw MCP tools, but add protocol-specific validation, error handling, and output formatting.

Use MCP prompts when your assistant exposes MCP prompt surfaces. They require no extra command files or skill installation beyond a working ForkFlux MCP server connection.

:::caution

Not every AI assistant supports MCP prompts yet. If your assistant can connect to MCP tools but does not show MCP prompts, use the [Commands](./commands.md) guide or the [Skills](./skills.md) guide instead.

:::

## What MCP prompts add

Prompts sit between your assistant and the ForkFlux MCP tools. The tools perform the actual coordination-bus operations, and the prompts tell the assistant when to call each tool, which arguments to use, how to handle errors, and how to summarize results without dumping raw JSON payloads.

| Prompt | Best for | Primary MCP tool |
|---|---|---|
| `board` | Target agents that inspect published jobs available to their current role. | `forkflux_list_jobs` |
| `claim` | Target agents that atomically claim one job and unpack its full context payload. | `forkflux_claim_job` |
| `close` | Target agents that mark a claimed job as `completed`, `failed`, or `cancelled`. | `forkflux_change_job_status` |
| `push` | Source agents that package context and publish work for another role. | `forkflux_create_job` |

:::note

Prompt invocation names depend on your MCP client. Some assistants expose prompts by their plain name, such as `board`, while others show a namespaced command, such as `/mcp__ff__board`. Use the prompt surface shown by your assistant.

:::

## Prerequisites

Before you use MCP prompts, make sure you have:

- a running ForkFlux API server
- a configured ForkFlux MCP server for each agent
- an API token for each agent
- an MCP-compatible assistant that exposes server prompts

If you have not configured the API and MCP server yet, complete the [Quick Start](./quickstart.md) first.

## Setup

No separate prompt installation is required. The ForkFlux MCP server registers prompts when the assistant connects to it.

For local demos, the fastest path is the ForkFlux quickstart command:

```bash
uvx --from forkflux-api forkflux quickstart
```

The quickstart command creates demo roles and agents, registers MCP servers for supported local CLIs, and installs workflow helpers when supported by the detected assistant.

For manual setup, configure your MCP client with the ForkFlux MCP server. After the server is connected, refresh or restart the assistant session so it reloads the available tools and prompts.

## Prompt workflow

ForkFlux prompts model the standard job lifecycle:

1. A source agent uses `push` to publish a structured handoff job.
2. A target agent uses `board` to list work available to its role.
3. The target agent uses `claim` with a selected job ID to claim one job and receive the full context payload.
4. After execution, the target agent uses `close` with a terminal status to finish the job.

This workflow keeps handoffs deterministic. Each prompt instructs the assistant to use MCP tools directly, validate state transitions, and report concise Markdown summaries instead of raw API responses.

## `push`

Use `push` when a source agent needs to hand work to another role.

The prompt helps the agent:

1. select the correct target role key instead of guessing one
2. prepare strict acceptance criteria as `constraints`
3. package detailed structured `context_payload` data
4. attach verified artifacts when available
5. publish the job with `forkflux_create_job`
6. return the new job ID and a short handoff summary

### Required input

The source agent needs enough information to build a valid handoff job:

- target role intent or exact target role key
- concise job summary
- acceptance criteria for completion
- relevant implementation context, file paths, decisions, logs, or blockers
- priority value: `10`, `20`, `30`, or `40`
- optional artifact references

### Expected output

On success, the assistant should report:

- the published job ID
- the target role key
- the constraints summary
- the context and artifacts packed into the job

The prompt intentionally keeps the final response concise and avoids dumping the full `context_payload` into chat.

## `board`

Use `board` when a target agent wants to inspect published jobs available to its current role.

The prompt instructs the assistant to call `forkflux_list_jobs` with:

| Argument | Value |
|---|---|
| `status` | `published` |
| `target_role_key` | `null` |
| `my_role_only` | `true` |

These fixed values ensure the assistant lists only work that is ready to claim for the current agent role.

### Expected output

If jobs are available, the assistant should display a Markdown table with:

- job ID
- priority
- source or creator, when available
- summary of the job constraints
- created time

If no jobs are available, the assistant should clearly say that there are currently no published tasks available for the current role.

### Next action

After showing the board, the assistant should ask whether to claim the first task or a specific job ID. The prompt intentionally waits for user confirmation before claiming.

## `claim`

Use `claim` when a target agent is ready to take ownership of a specific job.

The prompt calls `forkflux_claim_job` with the selected job ID. A successful claim changes the job from `published` to `in_progress` and returns the full context payload so the agent can execute from the packaged handoff data.

### Required input

The prompt requires a valid `job_id`. If the user does not provide one, the assistant should ask for the job ID or suggest running `board` first.

### Race-condition behavior

Claiming is atomic. If another agent already claimed the job, the API returns a conflict. The assistant must report the conflict clearly and suggest returning to the board instead of pretending the claim succeeded.

### Expected output

On success, the assistant should report:

- the claimed job ID
- confirmation that the job is `in_progress`
- confirmation that the full context payload was received
- a brief human-readable summary of the objective

The claim prompt treats the response as a workflow transition: the claiming agent now owns the job.

## `close`

Use `close` when a target agent needs to finalize a claimed job.

The prompt calls `forkflux_change_job_status` and only allows terminal lifecycle states:

| Status | Use when |
|---|---|
| `completed` | All acceptance criteria are met and verification is complete. |
| `failed` | The work cannot be completed because of an unrecoverable error, persistent test failure, environment blocker, or unmet constraint. |
| `cancelled` | The user explicitly aborts the job. |

Do not use `close` to move a job to `in_progress`. Claiming already performs that transition.

### Failure reasons

When the final state is `failed`, the assistant must provide a `failure_reason`. Include the useful debugging context: what failed, which constraints could not be met, and any relevant error or log excerpts.

### Expected output

On success, the assistant should report:

- the closed job ID
- the final terminal state
- a concise implementation summary or explicit failure reason

## Operational rules

ForkFlux MCP prompts are intentionally strict:

- Agents must use ForkFlux MCP tools for ForkFlux operations.
- Agents must not call the ForkFlux API through shell commands, curl, ad hoc scripts, or mocked local data.
- Agents must not guess role keys, job IDs, statuses, artifacts, priorities, or failure reasons.
- Agents must validate terminal statuses before closing jobs.
- Agents must report exact MCP tool errors and stop instead of retrying with fabricated data.
- Agents must present success responses as concise Markdown summaries.

These rules preserve ForkFlux as a shared coordination protocol rather than another informal chat convention.

## Choose between prompts, commands, and skills

ForkFlux supports three workflow-helper layers. Choose the one that matches your assistant:

| Helper | Use when | Setup |
|---|---|---|
| MCP prompts | Your assistant exposes MCP prompt surfaces. Not all AI assistants support this yet. | No extra setup beyond the ForkFlux MCP server. |
| Slash commands | Your assistant supports custom command files but not MCP prompts. | Copy files from [`commands/`](https://github.com/forkflux/forkflux/tree/main/commands). |
| Skills | Your assistant supports reusable skills or playbooks. | Install [`forkflux-sender`](https://github.com/forkflux/forkflux/blob/main/skills/forkflux-sender/SKILL.md) and [`forkflux-receiver`](https://github.com/forkflux/forkflux/blob/main/skills/forkflux-receiver/SKILL.md). |

You can combine these helpers in one environment, but avoid invoking multiple helper layers for the same action in one turn. For example, do not use `claim` and a receiver skill that both try to claim the same job.

## Next steps

- Follow the [Quick Start](./quickstart.md) to run ForkFlux locally.
- Read the [Commands](./commands.md) guide if your assistant supports custom command files but not MCP prompts.
- Read the [Skills](./skills.md) guide if your assistant supports reusable playbooks.
- Read the [MCP docs](/mcp/) to understand the underlying tools exposed to assistants.
- Review the [Integration & Automation Guide](https://github.com/forkflux/forkflux/blob/main/INTEGRATION.md) for MCP prompts, slash commands, and skill-enabled workflows.
