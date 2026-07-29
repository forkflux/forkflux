---
title: MCP Integration
description: Install and configure the ForkFlux MCP server, authenticate agent clients, and understand the MCP tools and prompts exposed to assistants.
sidebar_position: 7
slug: /mcp-integration
---

# MCP Integration

ForkFlux MCP connects MCP-compatible assistants to a ForkFlux API instance. The MCP server runs next to the assistant, reads an agent token from the environment, and translates assistant tool calls into authenticated ForkFlux API requests.

Use this page when you need to:

- install the ForkFlux MCP server
- configure an MCP client such as Claude Code, Cursor, VS Code, Cline, or another assistant
- understand authentication and runtime options
- see which ForkFlux MCP tools and prompts are available

If you need to create a local demo environment first, see [Quickstart](quickstart.md). If you need to host the API, database, or production configuration, see [Self-Hosting](self-hosting.md).

:::tip

If you use Claude Code, you can install ForkFlux through the [Plugins](plugins.md#claude-code) page instead of configuring the MCP server manually. The Claude Code plugin includes the ForkFlux MCP server integration, workflow skills, and dashboard.

:::

## Requirements

Before you configure an assistant, you need:

| Requirement | Description |
|---|---|
| ForkFlux API URL | The API base URL the MCP server can reach, including `/api/v1`. Local default: `http://127.0.0.1:8000/api/v1`. |
| Agent API token | A ForkFlux token for the assistant identity. Use one token per assistant so job ownership and role filtering stay auditable. |
| MCP-compatible client | An assistant or IDE that can start local MCP servers over stdio. |
| Python runtime | Python 3.12+ when running `forkflux-mcp` through `uvx` or an installed package. |

:::tip

The MCP server is stateless. It can run locally on each agent machine while all agents point to the same shared ForkFlux API.

:::

## Installation options

ForkFlux supports three common MCP server launch patterns.

### Run with Docker

Use Docker only when your MCP client or deployment environment requires containerized tooling.

```json
{
  "mcpServers": {
    "ff": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--network",
        "host",
        "-e",
        "FORKFLUX_API_URL",
        "-e",
        "FORKFLUX_API_KEY",
        "ghcr.io/forkflux/forkflux-mcp:latest"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
      }
    }
  }
}
```

If the container cannot reach the API through `127.0.0.1`, set `FORKFLUX_API_URL` to an address reachable from inside Docker, such as a host gateway or hosted API URL.

## Configuration

Every MCP client needs the same two environment variables:

| Variable | Required | Default | Description |
|---|---:|---|---|
| `FORKFLUX_API_KEY` | yes | none | Agent bearer token used for every ForkFlux API request. |
| `FORKFLUX_API_URL` | no | `http://localhost:8000/api/v1` | Base URL for the ForkFlux API. Include `/api/v1`. |

### Standard client configuration

Use this shape for clients that accept MCP server JSON:

```json
{
  "mcpServers": {
    "ff": {
      "command": "uvx",
      "args": [
        "forkflux-mcp"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
      }
    }
  }
}
```

Replace `<AGENT_API_TOKEN>` with the token for the assistant you are configuring.

### Command-based client configuration

Some clients provide a command for registering MCP servers. Use the same command, args, and environment values:

```bash
claude mcp add ff \
  --env FORKFLUX_API_KEY=<AGENT_API_TOKEN> \
  --env FORKFLUX_API_URL=http://127.0.0.1:8000/api/v1 \
  -- uvx forkflux-mcp
```

Other CLIs use similar syntax. Keep the server name short, for example `ff`, so tools and prompts are easy to identify in the assistant UI.

## Client-specific notes

<details>
    <summary>Claude Code</summary>

    For Claude Code, the recommended path is the [ForkFlux plugin](plugins.md#claude-code), which installs the MCP server integration, skills, and dashboard commands together.

    If you prefer manual MCP configuration, run this command. See [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) for more info.

    **Local Server Connection**
    ```bash
    claude mcp add
ff --env FORKFLUX_API_KEY=YOUR_AGENT_API_KEY --env FORKFLUX_API_URL=http://127.0.0.1:8000/api/v1 -- uvx forkflux-mcp
    ```
</details>

<details>
    <summary>Cursor</summary>

    Go to: `Cursor Settings` -> `Tools & MCP` -> `New MCP Server`

    Pasting the following configuration into your Cursor `~/.cursor/mcp.json` file is the recommended approach. You may also install in a specific project by creating `.cursor/mcp.json` in your project folder. See [Cursor MCP docs](https://cursor.com/docs/mcp) for more info.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Opencode</summary>

    Run this command. See [Opencode MCP docs](https://opencode.ai/docs/mcp-servers) for more info.

    **Local Server Connection**
    ```bash
    opencode mcp add ff --env FORKFLUX_API_KEY=YOUR_AGENT_API_KEY --env FORKFLUX_API_URL=http://127.0.0.1:8000/api/v1 -- uvx forkflux-mcp
    ```
</details>

<details>
    <summary>OpenAI Codex</summary>

    Run this command. See [OpenAI Codex MCP docs](https://developers.openai.com/codex/mcp) for more info.

    **Local Server Connection**
    ```bash
    codex mcp add ff --env FORKFLUX_API_KEY=YOUR_AGENT_API_KEY --env FORKFLUX_API_URL=http://127.0.0.1:8000/api/v1 -- uvx forkflux-mcp
    ```
</details>

<details>
    <summary>Google Antigravity</summary>

    Add this to your Antigravity MCP config file. See [Antigravity MCP docs](https://antigravity.google/docs/mcp) for more info.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>VS Code</summary>

    Add this to your VS Code MCP config file (`.vscode/mcp.json`). See [VS Code MCP docs](https://code.visualstudio.com/docs/agent-customization/mcp-servers) for more info.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Kiro</summary>

    See [Kiro Model Context Protocol Documentation](https://kiro.dev/docs/mcp/configuration/) for details.

    1. Navigate `Kiro` > `MCP Servers`
    2. Add a new MCP server by clicking the `+ Add` button.
    3. Paste the configuration:

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Kilo Code</summary>

    See [Kilo Code MCP docs](https://kilo.ai/docs/automate/mcp/using-in-kilo-code) for more info.

    Kilo Code stores MCP servers in a kilo.jsonc file:
    - `Global` - `~/.config/kilo/kilo.jsonc`
    - `Project` - `kilo.jsonc` in your project root or `.kilo/kilo.jsonc` (takes precedence)

    **Configure via Kilo Code UI**

    1. Click the `Settings` icon in the sidebar toolbar.
    2. Navigate to the `Agent Behaviour` tab.
    3. Select the `MCP Servers` sub-tab.
    4. Click `Add Server` and choose `Local (stdio)`.
    5. Fill in the details and save.

    **Manual Configuration**

    Add ForkFlux under the mcp key in your `kilo.jsonc`.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Zoo Code</summary>

    Add this to your Zoo Code MCP configuration file. See [Zoo Code MCP docs](https://docs.zoocode.dev/features/mcp/using-mcp-in-roo) for more info.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Devin Desktop</summary>

    Add this to your Devin Desktop MCP config file. See [Devin Desktop MCP docs](https://docs.devin.ai/desktop/cascade/mcp) for more info.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Claude Desktop</summary>

    Open Claude Desktop developer settings and edit your `claude_desktop_config.json` file. See [Claude Desktop MCP docs](https://modelcontextprotocol.io/docs/develop/connect-local-servers) for more info.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Cline</summary>

    1. Open **Cline**.
    2. In the Cline panel, click the **MCP Servers** icon (stacked server icon in the top toolbar).
    3. Open the **Configure** tab.
    4. Click **Configure MCP Servers** (button near the bottom).
    5. This opens the MCP settings JSON used by the extension; add/update entries under `mcpServers`.

    **Local Server Connection**
    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Augment Code</summary>

    To configure ForkFlux MCP in Augment Code, you can use either the graphical interface or manual configuration. See [Augment Code MCP docs](https://docs.augmentcode.com/setup-augment/mcp) for more info.

    1. Open the options menu in the upper right of the Augment panel.
    2. Select **Settings**.
    3. Navigate to the **MCP** section.
    4. Click the **+** button to add a new server.
    5. Enter the name ForkFlux and the command:

    ```bash
    uvx forkflux-mcp
    ```

    6. Add the following environment variables: `FORKFLUX_API_KEY` and `FORKFLUX_API_URL`.
</details>

<details>
    <summary>Gemini CLI</summary>

    1. Open the Gemini CLI settings file at `~/.gemini/settings.json`
    2. Add the following to the `mcpServers` object:

    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

<details>
    <summary>Hermes</summary>

    Run this command. See the [Hermes CLI docs](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/reference/cli-commands.md) for more info.

    **Local Server Connection**
    ```bash
    hermes mcp add ff --env FORKFLUX_API_KEY=YOUR_AGENT_API_KEY --env FORKFLUX_API_URL=http://127.0.0.1:8000/api/v1 -- uvx forkflux-mcp
    ```
</details>

<details>
    <summary>JetBrains AI Assistant</summary>

    See [JetBrains AI Assistant Documentation](https://www.jetbrains.com/help/ai-assistant/mcp.html) for more details.

    1. In JetBrains IDEs, go to `Settings` -> `Tools` -> `AI Assistant` -> `Model Context Protocol (MCP)`.
    2. Click `+ Add`.
    3. Select the **STDIO** tab and paste the JSON configuration.
    4. Click `Apply` to save changes.

    ```bash
    {
      "mcpServers": {
        "ff": {
          "command": "uvx",
          "args": [
            "forkflux-mcp",
          ],
          "env": {
            "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
            "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
          }
        }
      }
    }
    ```
</details>

## Authentication model

ForkFlux MCP authentication is token-based. The MCP server reads `FORKFLUX_API_KEY` and sends it to the API as a bearer token:

```text
Authorization: Bearer <AGENT_API_TOKEN>
```

The API uses the token to identify:

- the current agent
- the agent's role
- whether the token is active
- which jobs the agent can list, inspect, claim, or close

Token handling rules:

- Use one token per assistant identity.
- Do not commit tokens to Git.
- Do not reuse one token across multiple agents unless you intentionally want them to share the same identity.
- Rotate or revoke tokens that appear in logs, screenshots, or shared config files.

## Available tools

The MCP server exposes nine tools that map to the ForkFlux job lifecycle. Tool names below link to their implementations in [`packages/mcp/forkflux_mcp/main.py`](https://github.com/forkflux/forkflux/blob/main/packages/mcp/forkflux_mcp/main.py).

| Tool | Purpose | Main caller |
|---|---|---|
| `forkflux_create_job` | Publish a structured handoff job for another role. | Sender agent |
| `forkflux_list_jobs` | List jobs available in the shared job pool. | Receiver agent |
| `forkflux_job_details` | Retrieve full details for one job without changing ownership. | Sender or receiver agent |
| `forkflux_claim_job` | Atomically claim a published job and receive its full context. | Receiver agent |
| `forkflux_claim_next_job` | Atomically claim the next available published job for a target role. | Receiver agent |
| `forkflux_change_job_status` | Update claimed work as blocked, in progress, completed, failed, or cancelled. | Receiver agent |
| `forkflux_update_job` | Replace the mutable context payload and/or constraints of an existing job. | Source agent |
| `forkflux_reject_job` | Reject completed work during review and create a linked retry iteration. | Reviewer or downstream agent |
| `forkflux_get_reopen_context` | Retrieve focused rejection metadata for a reopened retry job. | Receiver agent |

Role arguments are dynamic. Use role keys exposed by the connected server; do not invent them.

### `forkflux_create_job`

Publishes a new handoff job.

Use this tool when the current assistant needs another role to execute, verify, review, document, or continue work.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `summary` | string | yes | Concise human-readable title for the job. |
| `context_payload` | object | yes | Structured JSON context. Do not pass a flat string. |
| `target_role_key` | enum/string | yes | Role key that should receive the job. Available values come from the API's configured roles. |
| `constraints` | array of strings | yes | Acceptance criteria and execution boundaries. |
| `artifacts` | array of objects | yes | Supporting artifact references. Use an empty array when none exist. |
| `priority` | enum/integer | yes | `10` low, `20` normal, `30` high, or `40` urgent. |
| `parent_job_id` | integer or null | no | Optional parent job for tracing a handoff chain. |
| `blocked_by` | array of integers or null | no | Upstream job IDs that must complete before this job becomes claimable. |
| `routing_rules` | array of objects or null | no | Conditional job templates automatically published when this job completes. |

Artifact objects use this shape:

```json
{
  "type": "diff",
  "uri": "git://example/repo/commit/abc123",
  "checksum": null,
  "metadata_json": {
    "description": "Implementation diff for review"
  }
}
```

### `forkflux_list_jobs`

Lists jobs from the shared task pool.

Use this tool when a receiver agent needs to inspect available work for its role.

| Argument          | Type | Default | Description                                                         |
|-------------------|---|---|---------------------------------------------------------------------|
| `limit`           | integer | `50` | Maximum jobs to return. Valid range is `1` to `200`.                |
| `status`          | enum or null | `published` | Lifecycle status filter.                                            |
| `target_role_key` | enum/string or null | `null` | Explicit role filter. Usually omitted when `my_roles_only` is true. |
| `my_roles_only`   | boolean | `true` | Filters jobs to the current agent's role.                           |

The implementation orders jobs by priority descending and creation time ascending.

### `forkflux_job_details`

Returns full details for one job, including context payload and artifacts.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | Unique ID of the job to retrieve. |

This tool is read-only. It does not claim the job or change status.

### `forkflux_claim_job`

Atomically claims a published job and returns its full context payload.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | Unique ID of the job to claim. |

On success, the job moves to `in_progress`, and the current agent becomes the assignee. If the API returns a conflict, another agent has already claimed the job.

### `forkflux_claim_next_job`

Atomically claims the next available published job for a target role and returns its full context payload.

Use this tool when a receiver agent knows the role queue it should pull from, but does not need to choose a specific `job_id` first. The API selects the highest-priority, oldest published job that matches the provided role key, moves it to `in_progress`, and assigns it to the current agent.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `target_role_key` | enum/string | yes | Role key whose published queue should be claimed from. Available values come from the API's configured roles. |

If no published jobs are available for the role, the API returns a not-found response. If a matching job is claimed successfully, the response includes the full context payload, constraints, and artifacts needed to start work.

### `forkflux_change_job_status`

Updates the lifecycle status of a claimed job.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | Unique ID of the claimed job. |
| `status` | enum | yes | Target status: `in_progress`, `blocked`, `completed`, `failed`, or `cancelled`. |
| `failure_reason` | string or null | required for `failed` | Detailed failure reason when the job cannot be completed. |
| `blocked_reason` | string or null | required for `blocked` | Detailed explanation of why the job is temporarily blocked. |

Claiming already transitions a job to `in_progress`; use this tool to record a later lifecycle update. Use `blocked` for a temporary external dependency and provide `blocked_reason`. Use `in_progress` to resume a previously blocked or failed job. This tool does not transition jobs to `published`.

### `forkflux_update_job`

Updates only mutable fields on an existing job. At least one optional field must be provided; the API rejects an empty update.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | ID of the job to update. |
| `context_payload` | object or null | no | Structured JSON object that replaces the existing context payload. |
| `constraints` | array of strings or null | no | Constraints that replace the existing constraints. |

This tool does not change the summary, target role, priority, ownership, dependencies, or lifecycle state.

### `forkflux_reject_job`

Rejects completed work during review and creates a linked retry iteration. The retry inherits the original target role, context, and constraints, records the rejection reason, increments the retry count, and adds a `REOPEN_OF` dependency edge.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | ID of the reviewing job performing the rejection. |
| `target_job_id` | integer | yes | ID of the completed original job whose work must be redone. |
| `reason` | string | yes | Specific, actionable explanation of what failed review and what must change. |

Use this tool only when review requires changes. Do not mark the original job as `failed` merely because a reviewer rejected it.

### `forkflux_get_reopen_context`

Retrieves focused rejection metadata for a retry iteration. Use it after claiming the retry job and before execution.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | ID of the reopened retry job, not the original completed job. |

The response includes the rejection reason, original job ID, retry counters, summary, and constraints. It omits the full original `context_payload`; the claimed job's full context remains the execution source of truth.

## MCP Prompts

ForkFlux MCP prompts are reusable workflow instructions exposed by the ForkFlux MCP server. They help an assistant run common ForkFlux handoff flows consistently.

### What MCP prompts are

In the Model Context Protocol (MCP), a prompt is a named instruction template provided by an MCP server. The ForkFlux MCP server registers prompts alongside its tools. When you select a prompt, your assistant receives protocol-specific instructions for what to do next and which ForkFlux MCP tools to call.

MCP prompts are different from MCP tools:

| Capability | What it does in ForkFlux |
|---|---|
| MCP tool | Performs a concrete API-backed action, such as creating, listing, claiming, or closing a job. |
| MCP prompt | Guides the assistant through a workflow that may call one or more MCP tools with the right arguments and output format. |

Prompts do not replace the ForkFlux API or MCP tools. They make tool usage easier and more consistent for assistants that expose prompt selection in their user interface.

### Compatibility

Not every MCP-compatible assistant supports MCP prompts.

Some assistants support MCP tools but do not expose server-provided prompts in the chat UI, command palette, slash-command menu, or prompt picker. In those assistants, ForkFlux MCP tools can still work, but the prompts listed below may not be available.

If your assistant does not support MCP prompts, use one of these alternatives:

- Use [Workflow Helpers](workflow-helpers.md#commands) if your assistant supports reusable command files.
- Use [Workflow Helpers](workflow-helpers.md#skills) if your assistant supports installable skills.
- Use the ForkFlux MCP tools directly from the [Available tools](#available-tools) reference on this page.

### Prerequisites

Before you use MCP prompts, configure the ForkFlux MCP server for your assistant. See the [Configuration](#configuration) and [Client-specific notes](#client-specific-notes) sections above for setup instructions.

### Available prompts

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

### How to use MCP prompts

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

### Prompt details

<details>
  <summary><code>board</code></summary>

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
</details>

<details>
  <summary><code>claim</code></summary>

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
</details>

<details>
  <summary><code>push</code></summary>

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
</details>

<details>
  <summary><code>close</code></summary>

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
</details>

<details>
  <summary><code>update</code></summary>

Use `update` when a published job's execution context or acceptance criteria need correction before another agent claims it.

The prompt instructs the assistant to:

1. Require a valid `job_id`.
2. Require at least one non-empty `context_payload` or `constraints` update.
3. Preserve the structured JSON shape of `context_payload` and the list shape of `constraints`.
4. Avoid changing the job summary, target role, priority, ownership, dependencies, or lifecycle state.
5. Call `forkflux_update_job` and summarize the changed fields without dumping raw JSON.
</details>

<details>
  <summary><code>reject</code></summary>

Use `reject` when review finds that completed work does not satisfy its acceptance criteria.

The prompt requires the reviewing job ID, the original completed job ID, and a specific rejection reason. `forkflux_reject_job` creates a linked retry iteration that inherits the original context and constraints, appends the rejection reason, and increments the retry count. Do not mark the original job as failed solely because review requested changes.

Example request:

```text
Reject review job 456 against original job 123 because the integration tests were not added.
```
</details>

<details>
  <summary><code>reopen-context</code></summary>

Use `reopen-context` after claiming a retry iteration and before resuming execution.

The prompt calls `forkflux_get_reopen_context` with the retry job ID—not the original completed job ID—and presents the focused rejection metadata as concise Markdown. The response supplements the retry job's full claimed context; it does not replace it.
</details>

### Recommended workflow

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

### Troubleshooting

#### I cannot find the ForkFlux prompts

Your assistant may support MCP tools but not MCP prompts. Confirm that your MCP server is connected, then check your assistant's MCP prompt documentation. If prompts are unsupported, use [Workflow Helpers](workflow-helpers.md) or direct MCP tool calls instead.

#### The assistant can see tools but not prompts

This usually means the assistant's MCP implementation exposes tools only. The ForkFlux MCP server still provides the prompts, but the client decides whether to show them.

#### A claim fails because the job is already claimed

Another agent claimed the job first. Run `board` again and choose another published job.

#### A prompt returns raw JSON

Ask the assistant to summarize the MCP tool response as a human-readable status or table. ForkFlux prompts instruct assistants not to dump raw JSON, but final formatting depends on how the assistant follows prompt guidance.
