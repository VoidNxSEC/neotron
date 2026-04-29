"""
Neutron CLI Dock
Acts as the central command center for the project.
"""

import os
import subprocess
import sys
from pathlib import Path

import click

# Add project root to PYTHONPATH automatically
os.environ["PYTHONPATH"] = str(Path(__file__).parent.parent.parent.absolute())


def print_banner():
    click.secho(
        r"""
    _   __
   / | / /___  _  ____  _______
  /  |/ / __ \| |/_/ / / / ___/
 / /|  / /_/ />  </ /_/ (__  )
/_/ |_/\____/_/|_|\__,_/____/

🚀 Nexus Platform CLI - Mission Control
""",
        fg="cyan",
        bold=True,
    )


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    \b
    Nexus Enterprise-Grade AI Orchestration Platform
    Use this CLI to manage your environment, run servers, and test capabilities.
    """
    if ctx.invoked_subcommand is None:
        print_banner()
        click.echo(ctx.get_help())


@cli.command()
def status():
    """🔍 Show the current status of the Nexus environment and dependencies."""
    click.secho("\n🔍 Checking Nexus Environment Status...\n", fg="blue", bold=True)

    # Check dependencies
    try:
        import temporalio

        temporal_ok = click.style("✅ Installed", fg="green")
    except ImportError:
        temporal_ok = click.style("❌ Missing", fg="red")

    try:
        import fastapi

        fastapi_ok = click.style("✅ Installed", fg="green")
    except ImportError:
        fastapi_ok = click.style("❌ Missing", fg="red")

    click.echo(f"  Temporal SDK: {temporal_ok}")
    click.echo(f"  FastAPI:      {fastapi_ok}")

    # Configuration
    try:
        from neutron.core.config import get_config

        config = get_config()
        click.secho("\n⚙️  Configuration:", fg="yellow", bold=True)
        click.echo(f"  API Host: {config.api_host}:{config.api_port}")
        click.echo(f"  Primary LLM Provider: {config.llm.primary_provider.value}")
        click.echo(
            f"  Enabled LLM Providers: {[p.value for p in config.llm.get_enabled_providers()]}"
        )
        click.echo(
            f"  Smart Contracts: {'Enabled' if config.enable_smart_contracts else 'Disabled'}"
        )
    except ImportError as e:
        click.secho(
            f"  ❌ Error: Could not import core config. Are you in the 'uv run' environment? {e}",
            fg="red",
        )
    except Exception as e:
        click.secho(f"  ❌ Error loading config: {e}", fg="red")

    click.echo("")


@cli.command()
def features():
    """✨ Discover platform capabilities and defense-in-depth compliance."""
    click.secho("\n✨ NEXUS Platform Features & Capabilities ✨\n", fg="magenta", bold=True)

    click.secho("🛡️  Layer 1: SENTINEL (Application)", fg="cyan", bold=True)
    click.echo("    Python-level validation and business logic guards.")
    click.echo("    Checks outputs for GDPR/LGPD compliance natively.\n")

    click.secho("🛡️  Layer 2: BASTION (Kernel)", fg="cyan", bold=True)
    click.echo("    World's first kernel-level AI compliance using seccomp-BPF.")
    click.echo("    Physically prevents unauthorized data access at syscall level.\n")

    click.secho("🛡️  Layer 3: BASTION-SC (Smart Contracts)", fg="cyan", bold=True)
    click.echo("    On-chain compliance enforcement integrated with DeFi protocols.")
    click.echo("    Automatically reverts operations if consent is missing.\n")

    click.secho("🛡️  Layer 4: Audit Trail (Decentralized)", fg="cyan", bold=True)
    click.echo("    Immutable audit trails stored on IPFS & Arweave.")
    click.echo("    200+ year permanence for compliance tracking.\n")

    click.secho("🧠 Orchestration & Agents", fg="green", bold=True)
    click.echo("    Multi-agent swarm consensus (majority, unanimous, weighted).")
    click.echo("    Temporal.io workflows for durable, fault-tolerant execution.\n")


@cli.group()
def demo():
    """🎮 Run interactive system demos."""
    pass


@demo.command(name="phase2")
def demo_phase2():
    """Run Cerebro Optimizer Phase 2 demo."""
    run_script("scripts/demo_phase2.py")


@demo.command(name="ingestion")
def demo_ingestion():
    """Run Document Ingestion demo."""
    run_script("scripts/demo_document_ingestion.py")


@demo.command(name="bastion")
def demo_bastion():
    """Run BASTION Kernel-level Enforcement demo."""
    run_script("scripts/demo_bastion.py")


@demo.command(name="list")
def demo_list():
    """List all available interactive demos."""
    demo_dir = Path("scripts")
    if not demo_dir.exists():
        click.echo("No scripts directory found.")
        return

    click.secho("\n🎮 Available Demos:\n", fg="blue", bold=True)
    for script in sorted(demo_dir.glob("demo_*.py")):
        click.echo(f"  - {script.stem.replace('demo_', '')} (uv run python scripts/{script.name})")
    click.echo("")


@cli.command()
def worker():
    """⚙️  Start the Temporal orchestration worker."""
    click.secho("⚙️  Starting Temporal worker...", fg="green", bold=True)
    run_script("neutron/orchestration/worker.py", use_module=True)


@cli.command()
@click.option("--port", default=None, type=int, help="Override API port")
def api(port):
    """🌐 Start the Nexus FastAPI server."""
    click.secho("🌐 Starting Nexus API server...", fg="green", bold=True)
    try:
        import uvicorn

        from neutron.core.config import get_config

        config = get_config()

        target_port = port if port else config.api_port

        click.echo(f"API will be available at http://{config.api_host}:{target_port}")
        click.echo(f"Docs will be available at http://{config.api_host}:{target_port}/docs")

        uvicorn.run("neutron.api.server:app", host=config.api_host, port=target_port, reload=True)
    except ImportError as e:
        click.secho(
            f"❌ Import error: {e}. Ensure dependencies (uvicorn, fastapi) are installed.", fg="red"
        )
    except OSError as e:
        if "Address already in use" in str(e):
            click.secho(f"\n❌ Error: Port {target_port} is already in use.", fg="red", bold=True)
            click.echo(
                "You can specify a different port using: uv run python neutron/cli/main.py api --port 8001"
            )
        else:
            click.secho(f"❌ OSError: {e}", fg="red")
    except Exception as e:
        click.secho(f"❌ Failed to start API: {e}", fg="red")


def run_script(path: str, use_module: bool = False):
    """Helper to run a script in the current env."""
    click.secho(f"▶️ Executing: {path}", fg="yellow")
    env = os.environ.copy()

    if use_module:
        module = path.replace("/", ".").replace(".py", "")
        cmd = [sys.executable, "-m", module]
    else:
        cmd = [sys.executable, path]

    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.secho(f"\n❌ Execution failed with exit code {e.returncode}", fg="red", bold=True)
    except KeyboardInterrupt:
        click.secho("\n🛑 Execution interrupted by user", fg="yellow", bold=True)


def main():
    cli()


if __name__ == "__main__":
    main()
