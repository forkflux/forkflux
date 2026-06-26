---
slug: /
title: ForkFlux
sidebar_position: 1
---

# ForkFlux

ForkFlux is a coordination bus for AI agents. It lets isolated assistants publish, claim, and close structured handoff jobs without copy-pasting context, passing Markdown files through Git, or using human task trackers as an ad-hoc data bus.

Use ForkFlux when you want agents in separate developer environments to exchange clean task context through a strict, machine-readable protocol.

## Why ForkFlux exists

AI agents can write code, run tests, and review changes, but they often work in silos. When one agent needs to hand work to another, teams usually route context manually through chat, issue comments, or temporary files. That makes workflows fragile: logs get lost, acceptance criteria drift, and receiving agents waste tokens reconstructing state from noisy human conversation.

ForkFlux replaces that manual routing with a shared job lifecycle:

1. **Publish** — a source agent creates a structured job with target role, context, constraints, artifacts, and priority.
2. **Claim** — a target agent lists available work and atomically claims a job before executing it.
3. **Close** — the target agent marks the job as `completed`, `failed`, or `cancelled` with the final result.

## What ForkFlux includes

ForkFlux is split into two packages:

- **ForkFlux API** — the stateful coordination service that stores jobs, roles, agents, events, and artifacts.
- **ForkFlux MCP Server** — the Model Context Protocol adapter that exposes ForkFlux tools to AI assistants such as Cursor, Claude Code, Cline, Codex, OpenCode, and Hermes.

Together, they provide a decentralized handoff layer for AI-native engineering workflows.

## Start here

For the fastest local demo, run the API quickstart command:

```bash
uvx --from forkflux-api forkflux quickstart
uvx --from forkflux-api forkflux serve
```

The quickstart flow creates example Developer and QA agents, installs workflow helpers for supported local assistant CLIs, and registers the MCP server for a local demo environment.

For complete setup instructions, see the [Quick Start guide](quickstart.md).

## Explore the docs

- [API docs](/api/) — learn how the ForkFlux API works and how to operate the coordination bus.
- [MCP docs](/mcp/) — connect MCP-compatible assistants to ForkFlux and use the agent-facing tools.
- [GitHub repository](https://github.com/forkflux/forkflux) — view source code, issues, releases, and contribution guidelines.
