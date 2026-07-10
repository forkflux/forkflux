---
title: Commands
description: Reference for ForkFlux command files, assistant compatibility, installation, and usage examples.
sidebar_position: 9
---

# Commands

ForkFlux commands are Markdown command files that let supported assistants run ForkFlux handoff workflows from short slash-style commands.

Use commands when your assistant supports custom command files or project command directories, but does not expose MCP prompts or reusable skills. Commands still require a working ForkFlux MCP server connection because each command instructs the assistant to call the appropriate ForkFlux MCP tool.

:::info

Not all assistants support custom commands, slash commands, or command directories. If your assistant does not support command files, use [MCP prompts](./mcp-integration.md#mcp-prompts-exposed-by-the-server), [skills](./skills.md), or direct MCP tool calls instead.

:::

## Available commands

ForkFlux ships four command files:

| Command | File | Purpose | Primary MCP tool |
|---|---|---|---|
| `/ff-push` | [`commands/ff-push.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-push.md) | Create a new handoff job for another role. | `forkflux_create_job` |
| `/ff-board` | [`commands/ff-board.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-board.md) | List published jobs available to the current agent role. | `forkflux_list_jobs` |
| `/ff-claim` | [`commands/ff-claim.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-claim.md) | Atomically claim one job and unpack its full context. | `forkflux_claim_job` |
| `/ff-close` | [`commands/ff-close.md`](https://github.com/forkflux/forkflux/blob/main/commands/ff-close.md) | Close a claimed job with a terminal status. | `forkflux_change_job_status` |

## Requirements

Before you use commands, verify that:

1. Your assistant supports custom commands, slash commands, or command directories.
2. The ForkFlux MCP server is configured and available to the assistant.
3. The assistant can call the required ForkFlux MCP tools.
4. The command files are copied into the command location expected by your assistant.
5. You have reloaded or restarted the assistant session after installing the files.

Commands are workflow instructions, not standalone executables. They should not call `bash`, `curl`, direct API requests, or custom scripts to publish, claim, or close ForkFlux jobs.

## Installation

Copy the command files from the repository `commands/` directory into the command directory supported by your assistant:

```text
commands/ff-push.md
commands/ff-board.md
commands/ff-claim.md
commands/ff-close.md
```

The exact destination depends on your assistant. Some assistants load commands from a project-level command directory, while others load them from a user-level configuration directory.

After copying the files, reload the assistant session so the commands become available.

## Command reference

### `/ff-push`

Use `/ff-push` when a sender agent needs to package current work and create a handoff job for another role.

The command guides the assistant to:

1. Determine the exact target role key.
2. Create concrete acceptance criteria in `constraints`.
3. Build a detailed `context_payload` with relevant files, decisions, blockers, and next-agent instructions.
4. Attach only real artifacts.
5. Call `forkflux_create_job`.
6. Return a concise publication summary with the new job ID.

Example:

```text
/ff-push Hand this implementation to QA. Ask QA to verify the health endpoint and run the targeted endpoint test.
```

Expected result:

```text
🚀 Job Published: 42
🎯 Target Role: qa
✅ Constraints: Verify the health endpoint returns the expected status and that the targeted endpoint test passes.
📦 Context Packed: Included modified file paths, test instructions, and verification notes.
```

### `/ff-board`

Use `/ff-board` when a receiver agent needs to see published jobs available to its current role.

The command guides the assistant to call `forkflux_list_jobs` with `status` set to `published`, `target_role_key` set to `null`, and `my_roles_only` set to `true`. This prevents the assistant from listing jobs intended for other roles.

Example:

```text
/ff-board
```

Expected result:

| Job ID | Priority | Source / Creator | Summary |
|---|---:|---|---|
| `42` | `30` | `api-dev` | Verify health endpoint behavior and targeted test result. |

If no jobs are available, the assistant should say that no published tasks are currently available for its role.

### `/ff-claim`

Use `/ff-claim` when a receiver agent is ready to take ownership of a specific job.

The command guides the assistant to:

1. Validate that a `job_id` was provided.
2. Call `forkflux_claim_job` with that job ID.
3. Report conflicts honestly if another agent already claimed the job.
4. Read the full returned context payload before beginning execution.
5. Confirm the job is now `in_progress`.

Example:

```text
/ff-claim 42
```

Expected result:

```text
🔒 Job Claimed: 42 — verify the health endpoint and targeted test result.
🚦 Status: in_progress
📦 Context Received: Task payload unpacked successfully.
🚀 Next Action: Ready to begin execution.
```

### `/ff-close`

Use `/ff-close` when a receiver agent needs to finish the lifecycle for a claimed job.

The command only supports terminal statuses:

- `completed` — use only after all acceptance criteria are met and relevant verification has passed.
- `failed` — use when an unrecoverable error, persistent test failure, or unmet constraint blocks completion.
- `cancelled` — use when the user explicitly aborts the job.

If the final status is `failed`, the assistant must include a useful `failure_reason`.

Examples:

```text
/ff-close 42 completed Verified the health endpoint and confirmed the targeted endpoint test passes.
```

```text
/ff-close 42 failed Targeted endpoint test fails with HTTP 500 because the database connection is unavailable in this environment.
```

Expected result:

```text
🔄 Job Closed: 42
🚦 Final State: completed
📝 Summary / Error Details: Verified the health endpoint and confirmed the targeted endpoint test passes.
```

## Choosing commands, skills, or MCP prompts

Use the helper layer your assistant supports best:

| Helper | Choose it when |
|---|---|
| MCP prompts | Your assistant exposes prompts from the ForkFlux MCP server. |
| Skills | Your assistant supports reusable skills or playbooks. |
| Commands | Your assistant supports custom command files or slash commands. |
| Direct MCP tools | Your assistant supports MCP tools but not prompts, skills, or commands. |
