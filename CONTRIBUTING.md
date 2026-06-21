# Contributing to Vibhu-Oska

Thank you for your interest in contributing. Vibhu-Oska is a sovereign, locally-executed
AI operating layer — every contribution must uphold that principle. No cloud dependencies,
no external inference endpoints, no data leaving the host machine.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Branch Strategy](#branch-strategy)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Module Boundary Rules](#module-boundary-rules)

---

## Code of Conduct

All contributors are expected to interact with professionalism and respect.
Harassment, dismissiveness, or any form of discriminatory language will not be tolerated.
Violations should be reported to the project maintainer directly.

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/Inkesk-Dozing/Vibhu-Oska.git
cd Vibhu-Oska

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Unix

# Install the project in editable mode with all dependencies
pip install -e .
pip install -r requirements.txt

# Verify the install
python -c "from Backend.Gateway.App import app; print('Gateway OK')"
python -m pytest Tests/ -q
```

Copy `.env.example` to `.env` and fill in the required values before running the server.

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, tested, production-ready code |
| `feat/<name>` | New feature development |
| `fix/<name>` | Bug fixes |
| `refactor/<name>` | Internal restructuring without behavior change |
| `docs/<name>` | Documentation-only changes |
| `chore/<name>` | Tooling, config, dependency updates |

Always branch from `main`. Never push directly to `main`.

---

## Commit Conventions

This project enforces [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <short description>

[optional body]

[optional footer — e.g. Closes #12]
```

### Types

| Type | When to use |
|------|-------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code change that neither adds a feature nor fixes a bug |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Tooling, config, CI, dependency updates |
| `perf` | Performance improvement |

### Scopes (use one of)

`core`, `cognition`, `data`, `validation`, `orchestrator`, `eventbus`,
`gateway`, `model`, `frontend`, `plugins`, `infra`, `docker`, `proto`, `shared`

### Rules

- Subject line: imperative mood, no period, ≤72 characters.
- Body: explain **why**, not what the diff already shows.
- One logical unit per commit — do not batch unrelated changes.

---

## Pull Request Process

1. **Open an issue first** for anything non-trivial. Describe the problem clearly before
   proposing a solution.
2. **Link your PR to the issue** using `Closes #N` in the PR description.
3. **Keep PRs focused.** A PR that touches the model architecture and the frontend CSS
   is two PRs.
4. **Fill in the PR template** — summary, what changed, how to test, any breaking changes.
5. **Ensure the test suite passes** before requesting review:
   ```bash
   python -m pytest Tests/ -q
   ```
6. All PRs require at least one maintainer approval before merging.
7. Squash-merge is preferred to keep `main` history linear and readable.

---

## Code Standards

### Python

- Minimum version: **Python 3.11**
- Formatter: **Black** (`black .`)
- Linter: **Ruff** (`ruff check .`)
- Type hints are required on all public function signatures.
- Every public function must have a docstring stating:
  purpose, parameters, return value, and known edge cases.

### Imports

- **Absolute imports only.** No `sys.path.append()`, no relative path hacks (`../../`).
- The project is installed as an editable package. All imports resolve from the project root:
  ```python
  from Backend.Core.MainCore.CognitionCore.cognition import CognitionCore
  from Shared.Models import TaskResponse
  ```

### No magic numbers

All constants must be named and defined at module scope. No inline literals for timeouts,
thresholds, token limits, or similarity scores.

### File naming

| Artifact | Convention |
|----------|------------|
| Directories | `StrictCamelCase` (e.g. `CognitionCore`) |
| Python files | `StrictCamelCase` (e.g. `ValidationCore.py`) |
| Markdown files | `strict-lowercase-kebab.md` |
| Every directory | Must contain an `__init__.py` |

---

## Testing Requirements

- All new features must include tests in `Tests/`.
- Minimum coverage per PR: **happy path + one boundary condition + one adversarial input**.
- Tests must use in-memory SQLite and temporary ChromaDB collections — no disk state,
  no port binding, no network calls.
- Run the full suite before pushing:
  ```bash
  python -m pytest Tests/ -v --tb=short
  ```

---

## Module Boundary Rules

Vibhu-Oska has strict separation of concerns. Violating these boundaries will block a PR:

| Module | Responsibility | Hard Prohibitions |
|--------|---------------|-------------------|
| `OrchestratorCore` | Task coordination | Zero business logic |
| `CognitionCore` | Transformer reasoning | No DB connections, no I/O |
| `BackupCore` | Deterministic fallback | No heavy external libraries |
| `ValidationCore` | I/O contract enforcement | No processing logic |
| `DataCore` | Memory and graph retrieval | No inference logic |
| `Gateway` | HTTP/WS ingress only | No business logic, delegates to Orchestrator |

---

## Zero External Dependency Constraint

This is non-negotiable:

- No calls to OpenAI, Gemini, Anthropic, or any cloud inference API.
- No background binary services (Ollama, vLLM, LM Studio).
- All model weights and inference logic must exist as local project assets.
- Permitted deep-learning primitives: **PyTorch**, **NumPy**.

Any PR that introduces a cloud API call will be closed without review.
