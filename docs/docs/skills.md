---
title: Skills
description: Learn which ForkFlux skills are available, what each skill does, and how to install them in skill-enabled assistants.
sidebar_position: 8
---

# Skills

ForkFlux skills are reusable assistant playbooks that make agent handoffs predictable. They encode the sender and receiver workflows so agents use ForkFlux MCP tools directly, validate inputs, avoid raw JSON dumps, and report concise lifecycle updates.

Use this page when you want consistent ForkFlux behavior across sessions, agents, and local assistant tools that support skills or reusable instruction bundles.

## Available skills

ForkFlux ships two workflow skills:

| Skill | Purpose | Best for | Primary MCP tools |
|---|---|---|---|
| `forkflux-sender` | Packages current work into a structured handoff job for another role. | Source agents that need to publish work after local progress is ready for transfer. | `forkflux_create_job`, optionally `forkflux_change_job_status` |
| `forkflux-receiver` | Finds published jobs, claims one atomically, executes it locally, and closes the lifecycle. | Target agents that need to pull work from the shared task pool and report completion evidence. | `forkflux_list_jobs`, `forkflux_claim_job`, `forkflux_change_job_status` |

Both skills require the assistant to use MCP tools for ForkFlux workflow operations. Agents should not use shell commands, `curl`, custom scripts, mocked data, or direct API calls to publish, claim, or close jobs.

## `forkflux-sender`

Use `forkflux-sender` when an agent needs to hand off completed or transferable work to another role.

The skill guides the source agent to:

1. Verify the exact target role key before creating a job.
2. Convert the requested outcome into concrete acceptance criteria.
3. Build a structured `context_payload` with relevant files, decisions, blockers, and next-agent instructions.
4. Attach only real artifacts such as files, logs, diffs, reports, screenshots, or URLs.
5. Create a ForkFlux job with a valid priority.
6. Return a concise summary with the job ID, target role, constraints, and packed context.

Use this skill only when a handoff is explicit or when the current agent has completed local work and another role should continue, verify, review, or deploy it.

## `forkflux-receiver`

Use `forkflux-receiver` when an agent needs to receive work from ForkFlux.

The skill guides the target agent to:

1. List published jobs available to the current role.
2. Present the board as a readable table instead of raw JSON.
3. Claim the selected job atomically.
4. Unpack constraints, context, and artifacts before execution.
5. Execute the task locally.
6. Update the job as `blocked`, `completed`, `failed`, or `cancelled` with useful evidence, or resume blocked work as `in_progress`.

The receiver skill is strict about lifecycle states. It should not mark work as `completed` unless acceptance criteria are met and relevant verification has passed, and it should use `blocked` instead of `failed` for temporary blockers.

## Installation options

Choose the installation method that matches your assistant environment.

:::tip

If you use Claude Code, install ForkFlux through the [Plugins](plugins.md#claude-code) page. The Claude Code plugin installs the ForkFlux skills together with the MCP server integration and dashboard, so you do not need a separate skills installation step.

:::

### Option 1: Install through quickstart

For local demos and evaluation, run the ForkFlux quickstart command:

```bash
uvx --from forkflux-api forkflux quickstart
```

The quickstart flow sets up a local demo environment and installs supported workflow helpers for compatible local assistant CLIs.

Use this option when you want the shortest path to a working multi-agent demo.

:::caution

`forkflux quickstart` can modify local assistant CLI configuration. Use it for local demos and evaluation, not production setup.

:::

### Option 2: Install with the Skills CLI

If your assistant supports a Skills CLI, install the ForkFlux skill bundle:

```bash
npx skills add forkflux/forkflux
```

After installation, reload or restart the assistant session so it can discover the new skills.

### Option 3: Install manually

You can also copy the skill files directly from the repository:

- [`skills/forkflux-sender/SKILL.md`](https://github.com/forkflux/forkflux/blob/main/skills/forkflux-sender/SKILL.md)
- [`skills/forkflux-receiver/SKILL.md`](https://github.com/forkflux/forkflux/blob/main/skills/forkflux-receiver/SKILL.md)

Keep each skill in its own directory and preserve the `SKILL.md` filename. A typical installed layout looks like this:

```text
<assistant-skills-directory>/
├── forkflux-sender/
│   └── SKILL.md
└── forkflux-receiver/
    └── SKILL.md
```

After copying the files, reload or restart the assistant. Then confirm that both `forkflux-sender` and `forkflux-receiver` appear in the assistant's available skill list.

## When to use skills instead of prompts or commands

Use skills when your assistant supports reusable playbooks and you want behavior to remain consistent across sessions. Skills are especially useful for teams because the workflow rules live in versioned files instead of ad hoc prompts.

Use MCP prompts when your assistant exposes prompt surfaces from the MCP server directly. Use command files when your assistant supports slash commands or project command directories but does not support reusable skills.
