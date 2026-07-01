---
title: Contributing
description: Learn how to contribute issues, documentation, workflow helpers, API changes, MCP improvements, and pull requests to ForkFlux.
sidebar_position: 10
---

# Contributing

ForkFlux welcomes contributions of all kinds: bug reports, feature ideas, documentation improvements, workflow patterns, API changes, MCP integration fixes, tests, and deployment examples.

Use this page to understand where to contribute, how to prepare a change, and what maintainers expect in a pull request.

## Community expectations

All contributors must follow the project Code of Conduct. Be respectful, specific, and constructive when discussing bugs, design tradeoffs, implementation details, and documentation gaps.

Helpful places to participate:

- GitHub issues: [`https://github.com/forkflux/forkflux/issues`](https://github.com/forkflux/forkflux/issues)
- Discord: [`https://discord.gg/wTJVctJwn3`](https://discord.gg/wTJVctJwn3)
- Repository: [`https://github.com/forkflux/forkflux`](https://github.com/forkflux/forkflux)

## Ways to contribute

### Report bugs

Open an issue when you find behavior that is broken, confusing, or undocumented.

Include:

- what you were trying to do
- what happened
- what you expected
- steps to reproduce
- relevant command output or MCP tool error
- API status code or validation code, when available
- package affected: API, MCP, docs, commands, or skills

Good bug reports help maintainers reproduce the issue without guessing your environment.

### Suggest features

Open an issue for feature ideas, workflow improvements, new helper commands, deployment patterns, or API enhancements.

Describe:

- the user problem
- the proposed behavior
- why existing workflows are insufficient
- which agents or roles benefit
- any compatibility concerns for the API or MCP tools

### Improve documentation

Documentation contributions are product contributions. Useful docs changes include:

- clearer setup instructions
- missing troubleshooting cases
- better API examples
- workflow diagrams
- guide patterns from real usage
- corrected command, prompt, or skill behavior
- production deployment notes

When changing docs, keep the style consistent:

- use active voice
- prefer concrete examples over vague guidance
- keep one concept per section
- avoid raw JSON dumps unless they teach a schema or payload shape
- verify command examples against the current project behavior

### Improve workflow helpers

ForkFlux includes helper layers for agent workflows:

- MCP prompts exposed by the MCP server
- reusable skills in `skills/`
- slash command files in `commands/`

Workflow helper changes should preserve the core protocol rules:

- use ForkFlux MCP tools for ForkFlux operations
- do not instruct agents to call the API through shell commands or `curl`
- do not guess role keys, job IDs, statuses, priorities, artifacts, or failure reasons
- validate status transitions before closing jobs
- present concise Markdown summaries instead of raw API payloads

### Improve API or MCP code

ForkFlux is a monorepo with two main packages:

| Package | Purpose |
|---|---|
| `packages/api` | FastAPI coordination service for agents, roles, jobs, events, artifacts, and lifecycle transitions. |
| `packages/mcp` | Model Context Protocol server that exposes ForkFlux tools and prompts to assistants. |

Keep API and MCP changes aligned. If you change an API request, response, or lifecycle rule, update MCP tools, tests, and documentation in the same pull request when possible.

## Development setup

Clone the repository:

```bash
git clone https://github.com/forkflux/forkflux.git
cd forkflux
```

Create and activate a virtual environment:

```bash
uv venv
source .venv/bin/activate
```

Install dependencies:

```bash
uv sync --dev
```

Install pre-commit hooks:

```bash
pre-commit install
```

Run all pre-commit checks manually:

```bash
pre-commit run --all-files -c .pre-commit-config.yaml
```

## Testing expectations

Tests should match the package and layer you change.

### API package

For API changes:

- services should have unit tests
- repositories should have integration tests
- endpoint handlers should have integration tests
- integration tests should use factories

Run targeted API tests with:

```bash
uv run python -m pytest packages/api/tests/path/to/test_file.py -v --tb=short
```

Do not run the full test suite unless you intentionally need broad verification.

### MCP package

The MCP package follows a thin-wrapper pattern. MCP tools should call the central API request helper rather than duplicating HTTP logic.

For MCP tool tests:

- mock the API request helper directly
- do not mock the HTTP library for tool contract tests
- assert the helper is called once with the expected method, endpoint, and payload
- assert the tool returns the mocked helper result unchanged

Run targeted MCP tests with:

```bash
uv run python -m pytest packages/mcp/tests/test_tools.py -v --tb=short
```

### Documentation changes

For docs changes, build the Docusaurus site:

```bash
npm run build
```

Run this from the `docs` package directory.

## Commit style

ForkFlux uses Conventional Commits.

Format:

```text
<type>: short description
```

Examples:

```text
feat: add job event listing endpoint
fix: handle revoked agent tokens
docs: add self-hosting security checklist
test: cover claim conflict behavior
```

Common types:

| Type | Use for |
|---|---|
| `feat` | New features. |
| `fix` | Bug fixes. |
| `docs` | Documentation changes. |
| `style` | Formatting-only changes. |
| `refactor` | Code restructuring without behavior changes. |
| `perf` | Performance improvements. |
| `test` | Test additions or fixes. |
| `chore` | Maintenance tasks. |
| `ci` | CI configuration changes. |
| `build` | Build system or dependency changes. |
| `revert` | Reverting a previous change. |

## Pull request checklist

Before opening a pull request:

- [ ] Fork the repository and create a focused feature branch.
- [ ] Keep the change scoped to one problem or feature.
- [ ] Add or update tests for behavior changes.
- [ ] Update docs for user-visible behavior changes.
- [ ] Run targeted tests for the files or package you changed.
- [ ] Run pre-commit checks.
- [ ] Use a Conventional Commit message.
- [ ] Describe the motivation, implementation, and verification in the PR body.

For PR descriptions, include:

- **What changed** — concise summary.
- **Why** — problem or use case.
- **How verified** — exact commands or docs build result.
- **Docs impact** — docs changed or why docs are not needed.
- **Compatibility** — any API, MCP, prompt, command, or skill behavior changes.

## Review guidance

Maintainers review for:

- correctness of the protocol lifecycle
- safe agent behavior
- API and MCP compatibility
- test coverage at the right layer
- clear documentation
- security impact of tokens, context payloads, and artifacts
- backwards-compatible migration path when behavior changes

Review feedback is part of the collaboration process. Keep discussions specific, reference the relevant code or docs, and prefer small follow-up commits over broad rewrites.

## Code of Conduct

ForkFlux follows the project Code of Conduct. Report unacceptable behavior through the channels listed in the repository Code of Conduct.

## License

ForkFlux is licensed under Apache-2.0. By contributing, you agree that your contributions are provided under the project license.
