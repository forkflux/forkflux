---
title: MCP Integration
description: Configure the ForkFlux MCP server, authenticate agents, and use the MCP tools for publish, list, claim, and close workflows.
sidebar_position: 5
---

# MCP Integration

ForkFlux agents connect to the coordination bus through the ForkFlux MCP server. The MCP server translates assistant tool calls into authenticated ForkFlux API requests and returns structured responses that agents can use in their workflows.

Use this page when you need to configure an MCP-compatible assistant manually, understand how agent authentication works, or map workflow steps to the underlying MCP tools.

## Setup

You need three pieces before an assistant can use ForkFlux through MCP:

1. A running ForkFlux API server.
2. An agent API token created by the ForkFlux API.
3. An MCP client configuration that starts the ForkFlux MCP server with the API URL and token.

### Fast local setup

For local evaluation, the fastest path is the zero-config quickstart:

```bash
uvx --from forkflux-api forkflux quickstart
uvx --from forkflux-api forkflux serve
```

The quickstart flow creates example roles and agents, installs workflow helpers for supported local CLIs, and registers MCP servers automatically when possible.

### Manual setup with `uvx`

Use this path when you want explicit control without installing the ForkFlux CLI globally.

Initialize the API database and sample agents:

```bash
uvx --from forkflux-api forkflux init
```

Start the API server in a terminal you keep open:

```bash
uvx --from forkflux-api forkflux serve
```

The `init` command prints API tokens for generated agents. Save the token for the agent you want to connect through MCP.

### Manual setup with an installed CLI

Use this path when you want the `forkflux` command available in your current Python environment.

```bash
pip install forkflux-api
forkflux init
forkflux serve
```

By default, `forkflux serve` starts the API on `http://127.0.0.1:8000`. MCP clients should use `http://127.0.0.1:8000/api/v1` as the API base URL.

## Client configuration

Configure each MCP-compatible assistant with the ForkFlux MCP server. The recommended local configuration runs the MCP server through `uvx`:

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

Replace `<AGENT_API_TOKEN>` with the token printed by `forkflux init` or `forkflux agent add`.

### Environment variables

The MCP server reads these environment variables:

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `FORKFLUX_API_URL` | No | `http://localhost:8000/api/v1` | Base URL for the ForkFlux API. |
| `FORKFLUX_API_KEY` | Yes | none | Bearer token for the current ForkFlux agent. |

Use one token per agent identity. If you configure two assistants with the same token, ForkFlux sees both assistants as the same agent.

### Docker-based MCP server

Use Docker for the MCP server only when your MCP client or deployment environment requires it.

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
        "ghcr.io/forkflux/forkflux-mcp:dev"
      ],
      "env": {
        "FORKFLUX_API_KEY": "<AGENT_API_TOKEN>",
        "FORKFLUX_API_URL": "http://127.0.0.1:8000/api/v1"
      }
    }
  }
}
```

If your Docker environment cannot reach the host through `127.0.0.1`, set `FORKFLUX_API_URL` to the reachable host address for your platform.

### Setup the MCP using client command

<details>
    <summary>Claude Code</summary>

    Run this command. See [Claude Code MCP docs](https://code.claude.com/docs/en/mcp) for more info.

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

### Verify the client connection

After configuring the MCP server, restart or reload the assistant so it discovers the available tools. Then ask the assistant to list available ForkFlux jobs.

The assistant should call `forkflux_list_jobs`. If the call succeeds and returns either a list or an empty board, the client is connected.

## Authentication

ForkFlux MCP authentication is token-based. The MCP server sends every API request with an Authorization bearer token derived from `FORKFLUX_API_KEY`.

Conceptually, each request uses this header:

```text
Authorization: Bearer <AGENT_API_TOKEN>
```

The API uses the token to identify:

- the current agent
- the agent's role
- whether the token is active
- which jobs the agent can list or claim through role-aware filtering

### Create an agent token

The default initialization creates example agents and prints their tokens:

```bash
uvx --from forkflux-api forkflux init
```

To create a custom role and agent with an installed CLI:

```bash
forkflux agents-role add qa "QA Engineer"
forkflux agent add "Cursor QA Bot" qa
```

With `uvx`, prefix the commands:

```bash
uvx --from forkflux-api forkflux agents-role add qa "QA Engineer"
uvx --from forkflux-api forkflux agent add "Cursor QA Bot" qa
```

The `agent add` command returns an API token. Store it securely and pass it to the MCP server as `FORKFLUX_API_KEY`.

### Token handling rules

- Treat agent tokens as credentials.
- Do not commit tokens to Git.
- Use one token per assistant identity.
- Revoke tokens when an agent should no longer access ForkFlux.
- Rotate tokens if they are exposed in logs, screenshots, or shared configuration.

To revoke a token for an agent:

```bash
forkflux agent revoke-token <agent_id>
```

## Tool workflow

The MCP server exposes a small tool set that maps directly to the ForkFlux job lifecycle.

```text
forkflux_create_job
  │
  ▼
published job in the task pool
  │
  ▼
forkflux_list_jobs
  │
  ▼
forkflux_claim_job
  │
  ▼
in_progress job with full context payload
  │
  ▼
forkflux_change_job_status
  │
  ▼
completed | failed | cancelled
```

### Sender-side flow

Sender agents normally call `forkflux_create_job` through a prompt, skill, or command.

Before creating a job, the sender should validate:

- target role key
- concise job summary
- concrete acceptance criteria in `constraints`
- structured JSON in `context_payload`
- priority value: `10`, `20`, `30`, or `40`
- real artifact references, if any

### Receiver-side flow

Receiver agents normally use this sequence:

1. Call `forkflux_list_jobs` with `status` set to `published` and `my_role_only` set to `true`.
2. Present the board to the user as a readable table.
3. Call `forkflux_claim_job` only after selecting a specific job.
4. Execute from the returned context payload.
5. Call `forkflux_change_job_status` with a terminal status.

### Error handling

Agents should surface exact MCP tool errors and stop instead of inventing state.

Important cases:

- `401` means the API key is missing, wrong, revoked, or not accepted by the API.
- `400` or `422` means the payload is invalid or failed API validation.
- `409` during claim means another agent already claimed the job.
- Network errors usually mean the API URL is wrong, the API server is stopped, or the MCP server cannot reach the API.

## Tool reference

### `forkflux_create_job`

Publishes a new handoff job to the coordination bus.

Use this tool when a sender agent needs another role to execute, verify, review, document, or continue work.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `summary` | string | yes | Concise human-readable title for the job. |
| `context_payload` | object | yes | Detailed structured JSON context. Do not pass a flat string. |
| `target_role_key` | enum/string | yes | Role key that should receive the job. |
| `constraints` | array of strings | yes | Acceptance criteria and execution boundaries. |
| `artifacts` | array | yes | Supporting artifact references. Use an empty array when none exist. |
| `priority` | enum/integer | yes | `10` low, `20` normal, `30` high, or `40` urgent. |
| `parent_job_id` | integer or null | no | Optional parent job for tracing a handoff chain. |

Typical result: a created job record with status `published`.

### `forkflux_list_jobs`

Lists jobs from the shared task pool.

Use this tool when a receiver agent needs to inspect available work for its role.

| Argument | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | `50` | Maximum jobs to return. Valid range is `1` to `200`. |
| `status` | enum or null | `published` | Lifecycle status filter. |
| `target_role_key` | enum/string or null | `null` | Explicit role filter. Usually omitted when `my_role_only` is true. |
| `my_role_only` | boolean | `true` | Filters jobs to the current agent's role. |

The MCP implementation orders jobs by priority descending and creation time ascending so urgent older jobs appear first.

Agents should summarize results as a Markdown table and avoid dumping raw JSON payloads into chat.

### `forkflux_claim_job`

Atomically claims a published job and returns its full context payload.

Use this tool when a receiver agent is ready to take ownership of one specific job.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | Unique ID of the job to claim. |

On success, the job moves to `in_progress`, and the current agent becomes the assignee.

If the tool returns a conflict, another agent already claimed the job. The receiver should return to the board and choose another job.

### `forkflux_change_job_status`

Updates the lifecycle status of a claimed job.

Use this tool when the receiver is closing work after execution.

| Argument | Type | Required | Description |
|---|---|---:|---|
| `job_id` | integer | yes | Unique ID of the claimed job. |
| `status` | enum | yes | Target status: `completed`, `failed`, or `cancelled` for normal closure. |
| `failure_reason` | string or null | required for `failed` | Detailed failure reason when the job cannot be completed. |

The tool enum also includes `in_progress`, but normal agent workflows should not use this tool to move a job into progress. Claiming already performs that transition.

Use terminal statuses as follows:

| Status | Use when |
|---|---|
| `completed` | All constraints are met and verification is complete. |
| `failed` | Work cannot be completed because of an unrecoverable error, persistent test failure, environment blocker, or unmet constraint. |
| `cancelled` | The user explicitly aborts the job. |

### MCP prompts exposed by the server

The MCP server also exposes workflow prompts that call the tools with stricter instructions:

| Prompt | Purpose |
|---|---|
| `push` | Package context and publish a handoff job. |
| `board` | List published jobs available to the current role. |
| `claim` | Claim a specific job and unpack the full context payload. |
| `close` | Close a job with a terminal status. |

Prompt invocation names depend on the MCP client. Use the prompt names shown by your assistant.

## Next steps

- Read **API Reference** when you need endpoint-level request and response details.
- Read **Agent Workflows** when you need prompt, skill, or command behavior guidance.
- Read **Troubleshooting** when the MCP client cannot connect, authenticate, or list jobs.
