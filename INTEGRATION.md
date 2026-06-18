## ⌨️ Automation: MCP Prompts, Slash Commands, and Skills

ForkFlux supports multiple ways of guiding your AI assistant through handoff workflows, depending on your client capabilities.

### Option 1: Native MCP Prompts (Recommended)
If your AI assistant natively supports the MCP Prompts surface (e.g., Claude Code), the instructions are already exposed by the server.
- **Setup:** No extra configuration is required beyond registering the ForkFlux MCP server. The prompts will be automatically available in your assistant's context.
- **Usage:** Prompts will automatically register in your assistant's context workspace. For instance, in Claude Code, you can invoke them directly using auto-complete names like:
```bash
/mcp__ff__board
```

#### Available MCP prompts


| Prompt            | Short description |
|-------------------|---|
| `/mcp__ff__push`  | Packages local context, artifacts, and constraints to publish a new job. |
| `/mcp__ff__board` | Lists available `published` jobs filtered to the current agent role. |
| `/mcp__ff__claim` | Atomically claims a job and fetches its full context to immediately start work. |
| `/mcp__ff__close` | Finalizes the task by updating its status to `completed` or `failed`. |

### Option 2: Reusable Slash Commands (Fallback)
If your assistant does not support prompt surfaces yet (or you use custom modes in tools like Roo Code / Cline), ForkFlux ships pre-built slash-command definitions in the [`commands/`](commands/) directory that map to the underlying MCP tools.

**How to set them up:**
1. Open your assistant's custom commands configuration directory.
2. Copy the configuration files from the [`commands/`](commands/) folder.
3. Maintain the original command names (e.g., `/ff-board`, `/ff-push`).
4. Reload your assistant session to activate the new slash commands.

#### Available commands

| Slash command | File                                               | Short description |
|---------------|----------------------------------------------------|---|
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
