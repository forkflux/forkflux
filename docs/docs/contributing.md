---
title: Contributing
description: Quick guide for contributing to ForkFlux.
sidebar_position: 14
---

# Contributing

ForkFlux welcomes small, focused contributions: bug reports, feature ideas, documentation fixes, tests, API changes, and MCP improvements.

## Start here

- Follow the project Code of Conduct.
- Open an issue before large or behavior-changing work.
- Keep pull requests focused on one problem.
- Update tests and docs when user-visible behavior changes.

Useful links:

- GitHub issues: [`https://github.com/forkflux/forkflux/issues`](https://github.com/forkflux/forkflux/issues)
- Discord: [`https://discord.gg/wTJVctJwn3`](https://discord.gg/wTJVctJwn3)
- Repository: [`https://github.com/forkflux/forkflux`](https://github.com/forkflux/forkflux)

## Report a bug

Open an issue and include:

- what you tried to do
- what happened
- what you expected
- steps to reproduce
- relevant command output, API error, or MCP tool error

## Suggest a feature

Open an issue and describe:

- the user problem
- the behavior you want
- why the current workflow is not enough

## Make a change

Clone the repository and install dependencies:

```bash
git clone https://github.com/forkflux/forkflux.git
cd forkflux
uv sync --dev
pre-commit install
```

Run focused checks for the area you changed:

```bash
uv run python -m pytest path/to/test_file.py -v --tb=short
pre-commit run --all-files -c .pre-commit-config.yaml
```

For documentation changes, build the docs site from the `docs` package:

```bash
npm run build
```

## Commit style

ForkFlux uses Conventional Commits:

```text
<type>: short description
```

Common types:

- `feat` for new features
- `fix` for bug fixes
- `docs` for documentation changes
- `test` for test changes
- `chore` for maintenance

Examples:

```text
docs: simplify contributing guide
fix: handle revoked agent tokens
feat: add job event listing endpoint
```

## Pull request checklist

Before opening a pull request, make sure you have:

- [ ] created a focused branch
- [ ] added or updated tests when behavior changed
- [ ] updated documentation when users need to know about the change
- [ ] run the relevant checks
- [ ] used a Conventional Commit message, such as `docs: simplify contributing guide`
- [ ] explained what changed, why it changed, and how you verified it

## License

ForkFlux is licensed under Apache-2.0. By contributing, you agree that your contributions are provided under the project license.
