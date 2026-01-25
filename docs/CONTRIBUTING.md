# Contributing to NEXUS

First off, thanks for taking the time to contribute! 🎉

The NEXUS Platform is an enterprise-grade AI orchestration system. We value engineering rigor, test coverage, and strict compliance adherence.

## 🛠️ Development Environment

We enforce a **hermetic development environment** using Nix. This ensures that everyone uses the exact same versions of Python, CUDA, System Libraries, and tools.

### Prerequisites

1.  **Linux** (NixOS, Ubuntu, Fedora, etc.) or **macOS**.
2.  **Nix Package Manager** installed with Flakes enabled.

```bash
# Install Nix (Multi-user)
sh <(curl -L https://nixos.org/nix/install) --daemon
```

### Setting Up

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/kernelcore/neutron.git
    cd neutron
    ```

2.  **Enter the Environment:**

    ```bash
    nix develop
    ```

    *This will download and configure Python 3.13, uv, Postgres, Docker, Just, and all other dependencies.*

3.  **Bootstrap the Infrastructure:**

    ```bash
    just up
    ```

    *This starts the Temporal Server, Ray Head, and Postgres/MLflow containers via docker-compose.*

## 🧪 Testing

We have a strict "No Test, No Merge" policy.

### Running Tests

We use `pytest` for all testing.

```bash
# Run the full suite (Unit + Integration)
just test

# Run only compliance tests (Fast)
just test-sentinel

# Run with coverage report
just coverage
```

### Test Structure

-   `tests/compliance`: LGPD/GDPR/AI Act guardrails.
-   `tests/orchestration`: Multi-agent consensus logic.
-   `tests/memory`: Vector store and retrieval.
-   `tests/integration`: End-to-end workflows.

## 🎨 Code Style

We follow strict typing and formatting rules.

-   **Formatter**: `ruff`
-   **Linter**: `ruff`
-   **Type Checker**: `mypy` (strict mode)

**Pre-commit checks:**

```bash
# Fix formatting automatically
just fmt

# Run lint checks
just lint
```

## 📝 Pull Request Process

1.  **Create a Branch**: Use conventional naming (e.g., `feat/add-soc2-compliance`, `fix/consensus-bug`).
2.  **Write Tests**: Ensure your feature is covered.
3.  **Documentation**: Update docstrings and `docs/` if you changed API behavior.
4.  **Changelog**: Add a one-line entry to `CHANGELOG.md`.
5.  **Submit PR**: CI must pass before review.

## 🛡️ Compliance & Security

**Critical Rule**: Never disable a compliance guardrail in production code.

If you are modifying `neutron/compliance`, you must:
1.  Run the full compliance test suite.
2.  Ensure no existing audit logs would be invalidated (schema compatibility).

## 🐛 Reporting Bugs

Please use the GitHub Issue templates. Include:
-   `nix --version`
-   Reproduction steps
-   Expected vs Actual behavior

---

**Happy Coding!** 🚀
