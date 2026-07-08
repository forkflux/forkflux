---
title: MCP Integration
description: Install and configure the ForkFlux MCP server, authenticate agent clients, and understand the MCP tools exposed to assistants.
sidebar_position: 7
---

# MCP Integration

ForkFlux MCP connects MCP-compatible assistants to a ForkFlux API instance. The MCP server runs next to the assistant, reads an agent token from the environment, and translates assistant tool calls into authenticated ForkFlux API requests.

Use this page when you need to:

- install the ForkFlux MCP server
- configure an MCP client such as Claude Code, Cursor, VS Code, Cline, or another assistant
- understand authentication and runtime options
- see which ForkFlux MCP tools are available

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

The MCP server exposes a small tool set that maps to the ForkFlux job lifecycle.

| Tool | Purpose | Main caller |
|---|---|---|
| `forkflux_create_job` | Publish a structured handoff job for another role. | Sender agent |
| `forkflux_list_jobs` | List jobs available in the shared job pool. | Receiver agent |
| `forkflux_job_details` | Retrieve full details for one job without changing ownership. | Sender or receiver agent |
| `forkflux_claim_job` | Atomically claim a published job and receive its full context. | Receiver agent |
| `forkflux_change_job_status` | Close claimed work as completed, failed, or cancelled. | Receiver agent |

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

| Argument | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | `50` | Maximum jobs to return. Valid range is `1` to `200`. |
| `status` | enum or null | `published` | Lifecycle status filter. |
| `target_role_key` | enum/string or null | `null` | Explicit role filter. Usually omitted when `my_role_only` is true. |
| `my_role_only` | boolean | `true` | Filters jobs to the current agent's role. |

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

### `forkflux_change_job_status`

Updates the lifecycle status of a claimed job.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | Unique ID of the claimed job. |
| `status` | enum | yes | Target status. Normal terminal values are `completed`, `failed`, and `cancelled`. |
| `failure_reason` | string or null | required for `failed` | Detailed failure reason when the job cannot be completed. |

The tool enum also includes `in_progress`, but normal receiver workflows should not use this tool to move a job into progress. Claiming already performs that transition.
