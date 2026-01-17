# Installation Guide

The NEXUS Platform is designed to be "Infrastructure-as-Code" first. We use **Nix Flakes** to provide a fully reproducible development environment.

## 🚀 Quick Start (Recommended)

This method ensures you have the exact same toolchain as the CI/CD server and other developers.

### 1. Install Nix

If you don't have Nix installed:

```bash
sh <(curl -L https://nixos.org/nix/install) --daemon
```

Enable "Flakes" (if not already enabled):

```bash
mkdir -p ~/.config/nix
echo "experimental-features = nix-command flakes" >> ~/.config/nix/nix.conf
```

### 2. Enter the Environment

```bash
# Clone the repo
git clone https://github.com/kernelcore/neutron.git
cd neutron

# Activate the shell
nix develop
```

You are now inside a shell with:
-   Python 3.13
-   `uv` (Package Manager)
-   `just` (Task Runner)
-   `docker` & `docker-compose`
-   PostgreSQL Client
-   CUDA Libraries (if on Linux with NVIDIA GPU)

### 3. Start Infrastructure

We use `just` to manage services.

```bash
# Start Temporal, Postgres, MLflow, Ray
just up
```

### 4. Verify Installation

```bash
# Run the compliance demo
python scripts/demo_sentinel.py
```

---

## 🐢 Manual Installation (Not Recommended)

If you cannot use Nix, you can install manually. **Warning**: You are responsible for system dependencies (CUDA, Postgres libs).

### Prerequisites
-   Python 3.11+
-   PostgreSQL 15+
-   Docker & Docker Compose

### Steps

1.  **Install Python Dependencies:**

    ```bash
    pip install poetry
    poetry install --with dev
    ```

2.  **Start Services:**

    ```bash
    docker-compose up -d
    ```

3.  **Set Environment Variables:**

    Create a `.env` file:
    ```bash
    cp .env.example .env
    ```

---

## 🐛 Troubleshooting

### `nix develop` fails on macOS
-   Ensure you have Rosetta 2 installed if on Apple Silicon.
-   NEXUS is primarily optimized for Linux (NixOS/Ubuntu).

### Docker Permission Denied
-   Ensure your user is in the `docker` group: `sudo usermod -aG docker $USER`.

### Database Connection Failed
-   Ensure port `5432` is not occupied by a system Postgres service.
-   Run `just infra-down` and then `just infra-up` to reset.
