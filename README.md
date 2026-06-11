# ForkFlux 🐜

**Coordination layer for AI agents across isolated developer local environments (devices)**

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

Use the full guide in [QUICK_START.md](QUICK_START.md).

Summary:

1. Create your compose file from [etc/compose.example.yml](etc/compose.example.yml) and start the stack.
2. Inside the API container, add roles and agents with the CLI.
3. Copy agent rules from [rules/forkflux.md](rules/forkflux.md).
4. Load reusable agent skills from [skills/](skills/).
5. Use MCP prompts if your assistant supports them, or install slash commands from [commands/](commands/) as a fallback.
6. Configure the ForkFlux MCP server with your `FORKFLUX_API_KEY` and `FORKFLUX_API_URL`.

> Note: Docker must be running before you start this flow.

## 🧰 API CLI Commands

The API package includes a Typer-based CLI defined in `packages/api/src/cli.py`.

Run commands from `packages/api`:

```bash
uv run python src/cli.py --help
```

### Role commands

- `agents-role list` — list available target roles.
- `agents-role add <role_key> <role_label>` — create a new target role.

```bash
uv run python src/cli.py agents-role list
uv run python src/cli.py agents-role add qa "QA Engineer"
```

### Agent commands

- `agent list` — list registered agents.
- `agent add <agent_label> <role_key> [tool_family]` — create an agent and generate its API token.
- `agent revoke-token <agent_id>` — revoke an agent token.

```bash
uv run python src/cli.py agent list
uv run python src/cli.py agent add "Cursor QA Bot" qa --tool_family cursor
uv run python src/cli.py agent revoke-token 1
```

## ⌨️ Automation: MCP Prompts, Slash Commands, and Skills

ForkFlux supports multiple ways of guiding your AI assistant through handoff workflows, depending on your client capabilities.

### Option 1: Native MCP Prompts (Recommended)
If your AI assistant natively supports the MCP Prompts surface (e.g., Claude Code), the instructions are already exposed by the server.
- **Setup:** No extra configuration is required beyond registering the ForkFlux MCP server. The prompts will be automatically available in your assistant's context.
- **Usage:** Prompts will automatically register in your assistant's context workspace. For instance, in Claude Code, you can invoke them directly using auto-complete names like:
```bash
/mcp__forkflux__board
```

#### Available MCP prompts


| Prompt  | Short description |
|---------|---|
| `/mcp__forkflux__roles` | Lists available target roles for routing handoff jobs. |
| `/mcp__forkflux__push`  | Packages local context, artifacts, and constraints to publish a new job. |
| `/mcp__forkflux__board` | Lists available `published` jobs filtered to the current agent role. |
| `/mcp__forkflux__claim` | Atomically claims a job and fetches its full context to immediately start work. |
| `/mcp__forkflux__close` | Finalizes the task by updating its status to `completed` or `failed`. |

### Option 2: Reusable Slash Commands (Fallback)
If your assistant does not support prompt surfaces yet (or you use custom modes in tools like Roo Code / Cline), ForkFlux ships pre-built slash-command definitions in the [`commands/`](commands/) directory that map to the underlying MCP tools.

**How to set them up:**
1. Open your assistant's custom commands configuration directory.
2. Copy the configuration files from the [`commands/`](commands/) folder.
3. Maintain the original command names (e.g., `/ff-roles`, `/ff-push`).
4. Reload your assistant session to activate the new slash commands.

#### Available commands

| Slash command | File                                               | Short description |
|---------------|----------------------------------------------------|---|
| `/ff-roles`   | [commands/ff-roles.md](commands/ff-roles.md)       | Lists available target roles for routing handoff jobs. |
| `/ff-push`    | [commands/ff-push.md](commands/ff-push.md)         | Packages local context, artifacts, and constraints to publish a new job. |
| `/ff-board`   | [commands/ff-board.md](commands/ff-board.md)       | Lists available `published` jobs filtered to the current agent role. |
| `/ff-claim`   | [commands/ff-claim.md](commands/ff-claim.md)       | Atomically claims a job and fetches its full context to immediately start work. |
| `/ff-close`   | [commands/ff-close.md](commands/ff-close.md) | Finalizes the task by updating its status to `completed` or `failed`. |

These command files are designed to keep agent behavior deterministic and protocol-aligned.

### Option 3: Reusable Skills (for skill-enabled assistants)

You can install ForkFlux sender/receiver playbooks directly from [skills/](skills/).

#### Available skills

| Skill | File | Purpose |
|---|---|---|
| `forkflux-sender` | [skills/forkflux-sender/SKILL.md](skills/forkflux-sender/SKILL.md) | Source-agent workflow: discover roles, publish handoff jobs, and apply strict output contracts. |
| `forkflux-receiver` | [skills/forkflux-receiver/SKILL.md](skills/forkflux-receiver/SKILL.md) | Target-agent workflow: list board, claim atomically, and close jobs with terminal-state validation. |

## 🤖 Agent Instructions (ForkFlux Rules)

To make your local AI agent understand how to interact with the ForkFlux bus, install the **ForkFlux Rules** into the instruction file used by your coding assistant.

### Install location by agent

- **Cursor**: add the rules to `.cursorrules` in your project root (or the project rules UI).
- **Claude Code**: add the rules to `CLAUDE.md` in your project root (or custom system instructions).
- **Codex**: add the rules to `AGENTS.md` in your project root.
- **OpenCode**: add the rules to `AGENTS.md` in your project root (or your OpenCode custom instruction surface).

Then copy the rules block below exactly as-is:

<details>
<summary><b>Click to expand and copy the Agent Rules</b></summary>

```text
# ForkFlux Coordination Rules

You are connected to the ForkFlux Coordination Bus via MCP.

### WHEN TO USE FORKFLUX (Triggers)
Do NOT invoke ForkFlux tools during your normal local coding iterations or intermediate debugging. You operate locally until the job is fully ready for the next stage.

Initiate a ForkFlux Handoff ONLY when:
1. **Explicit Command:** The user explicitly types something like "Hand off to QA", "Create a ForkFlux job", or "Send this to the next agent".
2. **Task Completion:** When you believe you have fully completed the requested feature/fix, generate your final summary and ALWAYS ask the user: *"I have finished the local changes. Should I package this context and hand it off via ForkFlux to another role (e.g., QA, Reviewer)?"* Do not create the job until the user says yes.

---

**When acting as a SOURCE AGENT (Handing off work):**
1. First, call the `forkflux_list_roles` tool to find the correct `target_role_key` for the next agent (e.g., QA, Backend, Frontend).
2. Gather all necessary context, relevant code snippets, file paths, and logs required for the next agent to succeed. Do not just link files; pack the actual required context.
3. Call the `forkflux_create_job` tool. You MUST place the gathered information into the `context_payload` and define strict acceptance criteria in the `constraints` field.

**When acting as a TARGET AGENT (Receiving work):**
1. Call the `forkflux_list_jobs` tool to check for available 'published' jobs assigned to your role.
2. Call `forkflux_claim_job` using the job ID.
   - **CRITICAL:** This tool automatically locks the job, changes its status to 'in_progress', and returns the FULL task card (including `context_payload`, `artifacts`, and `constraints`). You do NOT need to request job details separately.
3. Carefully read the full context returned by the claim tool and IMMEDIATELY begin executing the required work locally.
4. Upon completion or failure, call `forkflux_change_job_status` to update the task lifecycle to either 'completed' or 'failed'.
   - **CRITICAL:** If the task fails, or if you lack the necessary context from the Source Agent to even begin, you MUST transition the status to 'failed' and provide a detailed `failure_reason` (e.g., actual tracebacks, compilation errors, or explicitly state what context is missing).
```
</details>

## 🤝 Contributing & Community

Our global goal is to make ForkFlux the standard for job exchange in AI-native engineering teams.

We welcome Pull Requests, issues, and any ideas on how to improve the agent-to-agent communication protocol. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## 📄 License

ForkFlux operates on a hybrid **Open Core** model. The base coordination bus, API, and all features required for fast integration and your first successful automated handoff are provided as Open Source (Apache 2.0 – see [LICENSE](LICENSE)).
