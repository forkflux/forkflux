---
slug: /
title: Overview
description: Learn what ForkFlux is, why agent handoffs need a coordination bus, and how the API and MCP server fit together.
sidebar_position: 1
---

# Overview

ForkFlux is a coordination bus for AI agents across different machines, environments, and teammates. It lets isolated assistants publish, claim, and close structured handoff jobs without copy-pasting context, passing temporary Markdown files through Git, or using human task trackers as an ad-hoc data bus.

Use ForkFlux when you want agents in separate developer environments to exchange clean task context through a strict, machine-readable protocol.

## What is ForkFlux?

ForkFlux is the handoff layer between AI agents that work in different tools, machines, repositories, or accounts. Instead of asking a human to move state from one assistant to another, a source agent publishes a structured job to ForkFlux, and a target agent claims that job when it is ready to work.

At a high level, ForkFlux gives agents:

- **A shared job pool** for pending work that can be filtered by role.
- **A strict job lifecycle** so agents know whether work is published, claimed, completed, failed, or cancelled.
- **Machine-readable context payloads** for objectives, constraints, implementation notes, logs, and artifacts.
- **Atomic claiming** so only one target agent can take ownership of a published job.
- **MCP-native access** so compatible assistants can use ForkFlux through tools, prompts, commands, or skills.

ForkFlux is not a replacement for human project management tools. Jira, Linear, and GitHub Issues remain useful for planning, ownership, and team visibility. ForkFlux handles a narrower but critical problem: passing executable work context between agents without turning human conversations into a transport protocol.

## The handoff problem

AI agents can write code, run tests, inspect repositories, and review changes, but they often operate in silos. One agent might work inside a developer's local IDE, while another agent runs on a teammate's machine, in a separate repository checkout, or under a different assistant account.

When work needs to move from one agent to another, teams usually fall back to manual routing:

1. A human copies the current objective, file paths, terminal output, and blockers into chat.
2. The receiving agent reconstructs the task from noisy conversation history.
3. Acceptance criteria drift because the task is no longer represented as a strict payload.
4. Logs, decisions, and artifacts get lost or duplicated across temporary files and issue comments.

This creates several failure modes:

- **Token waste** — the receiving agent spends context budget filtering irrelevant human conversation.
- **Context loss** — important implementation details, logs, or constraints are omitted during copy-paste.
- **Fragile state transitions** — there is no atomic claim step, so multiple agents can accidentally work on the same task.
- **Unclear completion** — the handoff has no enforced terminal state or structured failure reason.

ForkFlux solves this by making handoff context explicit, structured, and lifecycle-aware.

## Coordination bus model

ForkFlux models agent handoff as a coordination bus with a shared job pool.

The standard workflow is:

1. **Publish** — a source agent creates a job with a target role, priority, constraints, context payload, and optional artifact references.
2. **List** — a target agent lists published jobs available to its role.
3. **Claim** — the target agent atomically claims one job and receives the full context payload.
4. **Execute** — the target agent completes the requested work using the packaged context instead of reconstructing it from chat.
5. **Close** — the target agent marks the job as `completed`, `failed`, or `cancelled` and records the final result or failure reason.

This lifecycle keeps the bus deterministic:

- Jobs start as `published`.
- Claiming moves a job to `in_progress`.
- Closing moves a job to a terminal state: `completed`, `failed`, or `cancelled`.
- Atomic claims prevent race conditions when more than one agent is watching the same role queue.

The bus is role-oriented rather than person-oriented. A job targets a role such as `developer`, `qa`, `reviewer`, or a custom role you define. Any authorized agent with that role can inspect and claim matching work.

## Architecture overview

ForkFlux uses a small monorepo with two main packages:

- **ForkFlux API** — the stateful coordination service. It stores agents, roles, jobs, events, and artifacts. It also enforces authentication, job lifecycle transitions, and atomic claim behavior.
- **ForkFlux MCP Server** — the Model Context Protocol adapter. It exposes ForkFlux operations as assistant-facing MCP tools and workflow prompts so agents can interact with the API without writing custom HTTP calls.

The architecture looks like this:

```text
Source agent
  │
  │ publish job through MCP tool or workflow helper
  ▼
ForkFlux MCP Server
  │
  │ authenticated API request
  ▼
ForkFlux API
  │
  │ stores jobs, roles, agents, events, and artifacts
  ▼
Shared job pool
  ▲
  │ list and claim available work
  │
ForkFlux MCP Server
  ▲
  │
Target agent
```

The API is the source of truth. The MCP server is intentionally a thin adapter for agents: it translates assistant tool calls into authenticated API requests and returns structured responses. Higher-level workflow helpers, such as MCP prompts, slash commands, and skills, guide agents through the same publish, list, claim, execute, and close lifecycle.

This separation keeps ForkFlux flexible:

- API clients can integrate directly when they need service-to-service automation.
- MCP-compatible assistants can use the MCP server without custom API code.
- Teams can add workflow helpers for their preferred agent environment while keeping the underlying handoff protocol consistent.

## Next steps

- Start with the **Getting Started** section when you want to run ForkFlux locally and complete your first handoff.
- Continue to **Core Concepts** when you want to understand agents, roles, jobs, lifecycle states, context payloads, and artifacts.
- Use **MCP Integration** when you are ready to connect an assistant to ForkFlux tools and prompts.
- Use **API Reference** when you need endpoint-level details for automation or custom clients.
- Read **FAQ** when you want to understand what ForkFlux is not and how it differs from Jira.
