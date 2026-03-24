"""
Neutron CLI Dock
Acts as the central command center for the project.
"""
import click
import os
import subprocess
import sys
from pathlib import Path

@click.group()
def cli():
    """🚀 Neutron Platform CLI - Mission Control Dock"""
    pass

@cli.command()
def status():
    """Show the current status of the Neutron environment."""
    click.echo("🔍 Checking Neutron Environment Status...")
    
    # Check dependencies
    try:
        import temporalio
        temporal_ok = "✅ Installed"
    except ImportError:
        temporal_ok = "❌ Missing"
        
    try:
        import mlflow
        mlflow_ok = "✅ Installed"
    except ImportError:
        mlflow_ok = "❌ Missing"
        
    click.echo(f"  Temporal SDK: {temporal_ok}")
    click.echo(f"  MLflow SDK:   {mlflow_ok}")
    
    # Configuration
    try:
        from neutron.core.config import get_config
        config = get_config()
        click.echo(f"\n⚙️  Configuration:")
        click.echo(f"  API Host: {config.api_host}:{config.api_port}")
        click.echo(f"  Primary LLM Provider: {config.llm.primary_provider.value}")
        click.echo(f"  Enabled LLM Providers: {[p.value for p in config.llm.get_enabled_providers()]}")
        click.echo(f"  Smart Contracts: {'Enabled' if config.enable_smart_contracts else 'Disabled'}")
    except ImportError:
        click.echo("  ❌ Error: Could not import neutron.core.config. Are you in the right environment?")
    except Exception as e:
        click.echo(f"  ❌ Error loading config: {e}")

@cli.group()
def demo():
    """Run interactive demos."""
    pass

@demo.command(name="phase2")
def demo_phase2():
    """Run Cerebro Optimizer Phase 2 demo."""
    run_script("scripts/demo_phase2.py")

@demo.command(name="ingestion")
def demo_ingestion():
    """Run Document Ingestion demo."""
    run_script("scripts/demo_document_ingestion.py")
    
@demo.command(name="list")
def demo_list():
    """List available demo scripts."""
    demo_dir = Path("scripts")
    if not demo_dir.exists():
        click.echo("No scripts directory found.")
        return
        
    click.echo("Available Demos:")
    for script in sorted(demo_dir.glob("demo_*.py")):
        click.echo(f"  - {script.stem}")

@cli.command()
def worker():
    """Start the Temporal orchestration worker."""
    click.echo("Starting Temporal worker...")
    run_script("neutron/orchestration/worker.py", use_module=True)

@cli.command()
def api():
    """Start the FastAPI server."""
    click.echo("Starting API server...")
    try:
        import uvicorn
        from neutron.core.config import get_config
        config = get_config()
        uvicorn.run("neutron.api.server:app", host=config.api_host, port=config.api_port, reload=True)
    except ImportError as e:
        click.echo(f"Import error: {e}. Ensure dependencies (uvicorn, fastapi) are installed.")
    except Exception as e:
        click.echo(f"Failed to start API: {e}")

def run_script(path: str, use_module: bool = False):
    """Helper to run a script in the current env."""
    click.echo(f"▶️ Executing: {path}")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd())
    
    if use_module:
        module = path.replace("/", ".").replace(".py", "")
        cmd = [sys.executable, "-m", module]
    else:
        cmd = [sys.executable, path]
        
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Execution failed with exit code {e.returncode}")
    except KeyboardInterrupt:
        click.echo("\n🛑 Execution interrupted by user")

def main():
    cli()

if __name__ == "__main__":
    main()
