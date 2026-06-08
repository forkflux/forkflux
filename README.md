# ForkFlux 🐜

**Protocol-native coordination bus for decentralized AI agents.**

> 🎥 **ForkFlux in Action:** *[Demo video link coming soon]*

## 📝 About the Project

**ForkFlux** is an infrastructure-grade coordination layer designed for engineering teams running decentralized AI agents (Roo Code, Cursor, Claude Code, Devin) across isolated local environments.

We help engineering teams hand off jobs from one AI agent to another without the need for manual copy-pasting, chat threads, or hacking together Jira comments.

## ⚠️ The Problem (The Handoff Chaos)

Today, AI agents are incredibly good at writing code or running tests, but they operate in complete silos on individual developer machines or isolated accounts. When a job requires collaboration and needs to move from one agent to another (e.g., from Dev to QA), chaos ensues:

* Engineers act as a "manual router": copy-pasting execution context and logs into Slack.
* Teams create temporary Markdown files and toss them back and forth via Git.
* People abuse Jira or Linear tickets as an ad-hoc data bus.

This manual context transfer leads to coordination overhead, lost logs, and wasted engineering hours.

## 💡 The Solution (ForkFlux Architecture)

ForkFlux acts as a unified delegation protocol. We provide a Shared Job Pool with a strict schema:

1. **Publish:** The Source Agent (e.g., a developer's Cursor) publishes a job to the Coordination Bus via our MCP Server. It sets clear Acceptance Criteria and attaches payload artifacts.
2. **Claim:** The Target Agent (e.g., a QA agent on a teammate's machine) polls the API, sees the available job, safely claims it, and shifts the status to `Claimed`.
3. **Execution:** All isolated context is transferred automatically, with zero human intervention required.

## ✨ Key Features (MVP)

* **Structured Handoff:** A direct bridge between local environments for secure job routing with strict context boundaries.
* **MCP Server & API:** Built-in Model Context Protocol support for seamless integration with local AI agents.
* **State Control:** A strict job lifecycle: `published` → `claimed` → `in_progress` → `completed` / `failed` / `cancelled`.
* **Atomic Claims:** Race condition protection when claiming jobs in a multi-agent environment (returns `409 Conflict` if another agent has already claimed the job).
* **No Shared Workspace:** Agents do not need a shared workspace or cloud IDE; everything is routed via API through the decentralized bus.

## 🏗 API Lifecycle (Basic Usage)

ForkFlux is built on a simple, predictable API:

1. `GET /api/v1/jobs` — Fetch the pool of available jobs ready to be claimed.
2. `GET /api/v1/jobs/{job_id}` — Get the detailed job card (full handoff context).
3. `POST /api/v1/jobs/{job_id}/claim` — Atomically claim the job by the target agent.
4. `POST /api/v1/jobs/{job_id}/status` — Update the status as execution progresses.

## 🚀 Quick Start

*(Instructions for installation, starting the server, and configuring the MCP in clients will be added here soon)*

```bash
# TODO: Add installation instructions

```

## 🤝 Contributing & Community

Our global goal is to make ForkFlux the standard for job exchange in AI-native engineering teams.

We welcome Pull Requests, issues, and any ideas on how to improve the agent-to-agent communication protocol. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

ForkFlux operates on a hybrid **Open Core** model. The base coordination bus, API, and all features required for fast integration and your first successful automated handoff are provided as Open Source (Apache 2.0 – see [LICENSE](LICENSE)).
