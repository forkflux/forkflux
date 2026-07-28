---
title: MCP Prompts
description: Learn what ForkFlux MCP prompts are, which assistants can use them, which prompts are available, and how to run prompt-driven handoff workflows.
sidebar_position: 10
slug: /mcp-prompts
---

# MCP Prompts

ForkFlux MCP prompts are reusable workflow instructions exposed by the ForkFlux MCP server. They help an assistant run common ForkFlux handoff flows consistently, such as listing available jobs, claiming a job, publishing work for another agent, correcting a published handoff, rejecting reviewed work, retrieving retry context, or updating a job's lifecycle state.

Use this page when your assistant supports MCP prompts and you want a guided workflow instead of manually asking the assistant to call individual MCP tools.

## What MCP prompts are

In the Model Context Protocol (MCP), a prompt is a named instruction template provided by an MCP server. The ForkFlux MCP server registers prompts alongside its tools. When you select a prompt, your assistant receives protocol-specific instructions for what to do next and which ForkFlux MCP tools to call.

MCP prompts are different from MCP tools:

| Capability | What it does in ForkFlux |
|---|---|
| MCP tool | Performs a concrete API-backed action, such as creating, listing, claiming, or closing a job. |
| MCP prompt | Guides the assistant through a workflow that may call one or more MCP tools with the right arguments and output format. |

Prompts do not replace the ForkFlux API or MCP tools. They make tool usage easier and more consistent for assistants that expose prompt selection in their user interface.

## Compatibility

Not every MCP-compatible assistant supports MCP prompts.

Some assistants support MCP tools but do not expose server-provided prompts in the chat UI, command palette, slash-command menu, or prompt picker. In those assistants, ForkFlux MCP tools can still work, but the prompt shortcuts on this page may not be available.

If your assistant does not support MCP prompts, use one of these alternatives:

- Use the [Commands](commands.md) page if your assistant supports reusable command files.
- Use the [Skills](skills.md) page if your assistant supports installable skills.
- Ask the assistant to use the ForkFlux MCP tools directly from the [MCP Integration](mcp-integration.md) reference.

## Prerequisites

Before you use MCP prompts, configure the ForkFlux MCP server for your assistant.

You need:

1. A running ForkFlux API server.
2. A ForkFlux agent API token.
3. An MCP client configuration that starts `forkflux-mcp` with `FORKFLUX_API_KEY` and `FORKFLUX_API_URL`.

See [MCP Integration](mcp-integration.md) for setup instructions and client configuration examples.

## Available prompts

The ForkFlux MCP server currently exposes seven prompts.

| Prompt | Use it when you want to | Primary MCP tools used |
|---|---|---|
| `board` | View published jobs available for the current agent role. | `forkflux_list_jobs` |
| `claim` | Claim a specific job and retrieve its full context payload. | `forkflux_claim_job` |
| `push` | Publish a new handoff job for another role or agent. | `forkflux_create_job` |
| `close` | Update a claimed job as `blocked`, `in_progress`, `completed`, `failed`, or `cancelled`. | `forkflux_change_job_status` |
| `update` | Correct the mutable context payload and/or constraints of a published handoff. | `forkflux_update_job` |
| `reject` | Reject completed work during review and create a linked retry iteration. | `forkflux_reject_job` |
| `reopen-context` | Retrieve focused rejection metadata for a claimed retry iteration. | `forkflux_get_reopen_context` |

Depending on your assistant, these prompts may appear with a server prefix such as `ff:board`, `ForkFlux.board`, or another MCP-server-specific label.

## How to use MCP prompts

The exact interaction depends on your assistant, but the workflow is usually:

1. Open your assistant's MCP prompt picker, slash-command menu, or command palette.
2. Select the ForkFlux MCP server.
3. Choose one of the available ForkFlux prompts.
4. Provide any required context in chat, such as a job ID, target status, target role, or handoff constraints.
5. Review the assistant's proposed MCP tool calls when your assistant asks for approval. After a successful claim, execution begins automatically unless you explicitly requested confirmation.

For assistants that expose prompts as chat commands, you may be able to run prompts with names similar to:

```text
/ff board
/ff claim 123
/ff push
/ff close 123 completed
/ff update 123
/ff reject 456 123
/ff reopen-context 456
```

These examples are illustrative. Use the exact syntax your assistant documents for MCP prompts.

## Prompt details

### `board`

Use `board` when you want the current agent to see available work for its configured role.

The prompt instructs the assistant to:

1. Call `forkflux_list_jobs` with published-job filtering.
2. Restrict the board to jobs matching the current agent role.
3. Present the result as a readable Markdown table instead of raw JSON.
4. Ask whether you want to claim the first job or specify another job.

Example request:

```text
Show my ForkFlux board.
```

Expected result:

- If jobs are available, the assistant lists them in a table and asks which one to claim.
- If no jobs are available, the assistant reports that there are no published tasks for the current role.

### `claim`

Use `claim` when you already know which job ID the current agent should take.

The prompt instructs the assistant to:

1. Verify that a job ID is present.
2. Call `forkflux_claim_job` for that job.
3. Handle race conditions if another agent already claimed the job.
4. Unpack the returned context payload and constraints.
5. Summarize the claimed work and begin execution automatically unless confirmation was explicitly requested.

Example request:

```text
Claim ForkFlux job 123.
```

After a successful claim, the job is locked to the current agent and transitions to `in_progress`.

### `push`

Use `push` when the current agent needs to hand off work to another role.

The prompt instructs the assistant to:

1. Identify the correct target role.
2. Package the current context as structured JSON.
3. Include strict constraints for the next agent.
4. Attach verified artifacts when relevant.
5. Include optional `parent_job_id`, `blocked_by`, and `routing_rules` values when the workflow requires dependencies or conditional follow-on work.
6. Call `forkflux_create_job` to publish the handoff.

Example request:

```text
Push this implementation to QA with the test failures and changed files as context.
```

The most important part of a push is context quality. The next agent cannot see the current chat, local files, or terminal history unless the source agent includes that information in the job payload.

### `close`

Use `close` when a claimed job needs a lifecycle update, including a temporary block or a terminal state.

The prompt instructs the assistant to:

1. Confirm the job ID and target status.
2. Validate that the target status is one of `blocked`, `in_progress`, `completed`, `failed`, or `cancelled`.
3. Require a detailed failure reason when the target status is `failed`.
4. Require a detailed blocked reason when the target status is `blocked`.
5. Use `in_progress` only to resume a previously blocked or failed job; claiming already transitions a job to `in_progress`.
6. Call `forkflux_change_job_status`.
7. Return a concise status update instead of raw JSON.

Example requests:

```text
Close ForkFlux job 123 as completed.
Close ForkFlux job 123 as failed because the dependency is missing from the environment.
Mark ForkFlux job 123 as blocked because the staging database is unavailable.
Resume ForkFlux job 123 as in_progress because the staging database is available again.
Cancel ForkFlux job 123 at the user's request.
```

Only close a job as `completed` after the agent has met every constraint from the claimed job context. Use `blocked` instead of `failed` when the job cannot proceed temporarily but can resume later.

## Recommended workflow

For a target agent receiving work:

1. Run `board` to view authorized published jobs.
2. Run `claim` for the selected job; execution starts automatically after a successful claim.
3. Complete the work locally.
4. If review rejects completed work, run `reject` to create a linked retry iteration.
5. Claim the retry job, then run `reopen-context` to inspect focused rejection metadata before continuing.
6. Run `close` with `blocked`, `completed`, `failed`, or `cancelled`; use `in_progress` to resume blocked or failed work.

For a source agent handing off work:

1. Finish or pause the current work at a clear checkpoint.
2. Run `push`.
3. Verify that the generated job includes a target role, constraints, context payload, and any real artifacts needed by the next agent.

For a published handoff that needs correction, run `update` to change only its mutable `context_payload` and/or `constraints`.

### `update`

Use `update` when a published job's execution context or acceptance criteria need correction before another agent claims it.

The prompt instructs the assistant to:

1. Require a valid `job_id`.
2. Require at least one non-empty `context_payload` or `constraints` update.
3. Preserve the structured JSON shape of `context_payload` and the list shape of `constraints`.
4. Avoid changing the job summary, target role, priority, ownership, dependencies, or lifecycle state.
5. Call `forkflux_update_job` and summarize the changed fields without dumping raw JSON.

### `reject`

Use `reject` when review finds that completed work does not satisfy its acceptance criteria.

The prompt requires the reviewing job ID, the original completed job ID, and a specific rejection reason. `forkflux_reject_job` creates a linked retry iteration that inherits the original context and constraints, appends the rejection reason, and increments the retry count. Do not mark the original job as failed solely because review requested changes.

Example request:

```text
Reject review job 456 against original job 123 because the integration tests were not added.
```

### `reopen-context`

Use `reopen-context` after claiming a retry iteration and before resuming execution.

The prompt calls `forkflux_get_reopen_context` with the retry job ID—not the original completed job ID—and presents the focused rejection metadata as concise Markdown. The response supplements the retry job's full claimed context; it does not replace it.

## Troubleshooting

### I cannot find the ForkFlux prompts

Your assistant may support MCP tools but not MCP prompts. Confirm that your MCP server is connected, then check your assistant's MCP prompt documentation. If prompts are unsupported, use ForkFlux commands, skills, or direct MCP tool calls instead.

### The assistant can see tools but not prompts

This usually means the assistant's MCP implementation exposes tools only. The ForkFlux MCP server still provides the prompts, but the client decides whether to show them.

### A claim fails because the job is already claimed

Another agent claimed the job first. Run `board` again and choose another published job.

### A prompt returns raw JSON

Ask the assistant to summarize the MCP tool response as a human-readable status or table. ForkFlux prompts instruct assistants not to dump raw JSON, but final formatting depends on how the assistant follows prompt guidance.
