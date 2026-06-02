# Contributing to ForkFlux

Thanks for your interest in contributing to ForkFlux! 🚀
We welcome contributions of all kinds — code, documentation, bug reports, ideas, and feedback.

---

## 📌 How to Contribute

### 1. Report Issues
If you've found a bug or have a feature request, please [open an issue](https://github.com/forkflux/forkflux/issues).
Be as descriptive as possible: what happened, what you expected, and steps to reproduce.

---

### 2. Suggest Features
We’re actively improving ForkFlux. If you have ideas, open a new issue and use the `feature` label.

---

### 3. Contribute Code

#### 📥 Clone the repo
```bash
git clone https://github.com/forkflux/forkflux.git
cd forkflux
```

#### 🧪 Run the project locally
1. Create a virtual environment
```bash
# Create a virtual environment
uv venv

# Activate it (macOS/Linux)
source .venv/bin/activate
# Or activate it (Windows)
# .\.venv\Scripts\activate

# Install all required libraries
uv sync
```

2. Install dependencies
```bash
uv sync --dev
```

3. Run tests
```bash
python -m pytest -s tests/
```

#### 🔄 Set up pre-commit
We use `pre-commit` to ensure consistent formatting and static analysis.

Install and set up hooks:
```bash
pre-commit install
```

To run checks manually:
```bash
pre-commit run --all-files -c .pre-commit-config.yaml
```

---

### ✍️ Commit Style

Please follow the [Conventional Commits](https://www.conventionalcommits.org/) convention:

```
<type>: short description
```

Examples:
- `feat: add support for Gemini model`
- `fix: handle error when env file is missing`
- `docs: update README with setup instructions`

**Allowed types:**
- `feat` – a new feature is introduced
- `fix` – a bug fix
- `docs` – documentation updates (e.g. README)
- `style` – formatting only (white-space, commas, etc.)
- `refactor` – code changes that don’t fix bugs or add features
- `perf` – performance improvements
- `test` – adding or fixing tests
- `chore` – other changes (e.g. dependency updates)
- `ci` – CI configuration changes
- `build` – build system or dependency-related changes
- `revert` – reverts a previous commit

---

### ✅ Submit a Pull Request
1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes and commit (`git commit -m "feat: add new feature"`)
4. Push to your fork and open a Pull Request

Please ensure all pre-commit hooks pass before submitting.

---

## 🤝 Code of Conduct
Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) when interacting in this project.

---

## 🙏 Thank You!
Your contributions help make ForkFlux better for everyone. We’re excited to have you here!
