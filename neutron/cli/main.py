"""
Neutron CLI Dock — Mission Control
===================================
Unified command center for the entire NEXUS Platform.
Covers: infra, worker, api, demos, pipelines, tests, checks,
cost tracking, ML artifact management, workflow monitoring,
Nix tooling, and project hygiene.

Architecture principle:
  One entry point. One source of truth. No drift.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import click

from neutron.events.cli_commands import event_group

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
os.environ["PYTHONPATH"] = str(PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
def print_banner():
    click.secho(
        r"""
    _   __
   / | / /___  _  ____  _______
  /  |/ / __ \| |/_/ / / / ___/
 / /|  / /_/ />  </ /_/ (__  )
/_/ |_/\____/_/|_|\__,_/____/

   N E X U S   P L A T F O R M
   Enterprise-Grade AI Agent Orchestration
   Compliance-as-Code  •  Defense-in-Depth
""",
        fg="cyan",
        bold=True,
    )


def print_welcome():
    """Rich welcome message with all available command groups."""
    print_banner()
    click.secho("═" * 62, fg="white", dim=True)
    click.secho(
        "  MISSION CONTROL — todos os comandos do ecossistema", fg="bright_white", bold=True
    )
    click.secho("═" * 62, fg="white", dim=True)
    click.echo()

    sections = [
        (
            "🔍 DIAGNÓSTICO",
            [
                ("neotron status", "Estado do ambiente, deps e configuração"),
                ("neotron features", "Capacidades da plataforma (4 camadas)"),
            ],
        ),
        (
            "🏗️ INFRAESTRUTURA",
            [
                ("neotron infra up", "Iniciar Temporal + MLflow + PostgreSQL + Ray"),
                ("neotron infra down", "Parar todos os serviços"),
                ("neotron infra status", "Status dos containers Docker"),
                ("neotron infra logs [svc]", "Logs da infra (ou de um serviço específico)"),
                ("neotron infra restart <svc>", "Reiniciar um serviço"),
                ("neotron infra health", "Health check de todos os endpoints"),
            ],
        ),
        (
            "⚙️ WORKER",
            [
                ("neotron worker start", "Iniciar Temporal Worker (foreground)"),
                ("neotron worker bg", "Iniciar Worker em background"),
                ("neotron worker stop", "Parar Worker em background"),
                ("neotron worker logs", "Visualizar logs do worker"),
            ],
        ),
        (
            "🌐 SERVIDORES",
            [
                ("neotron api [--port N]", "Subir API FastAPI (default porta 8000)"),
                ("neotron gui", "Subir interface GUI"),
                ("neotron ui", "Abrir todas as UIs no browser"),
            ],
        ),
        (
            "🎮 DEMOS",
            [
                ("neotron demo list", "Listar demos disponíveis"),
                ("neotron demo phase2", "Demo: Cerebro Optimizer Phase 2"),
                ("neotron demo ingestion", "Demo: Document Ingestion"),
                ("neotron demo bastion", "Demo: BASTION Kernel Enforcement"),
                ("neotron demo sentinel", "Demo: SENTINEL Compliance Guardrails"),
                ("neotron demo nexus", "Demo: Plataforma Completa"),
                ("neotron demo swarm", "Demo: Agent Swarm + Consensus"),
                ("neotron demo cortex", "Demo: Cortex Live Analysis"),
                ("neotron demo 4layer", "Demo: 4-Layer Defense-in-Depth"),
            ],
        ),
        (
            "🚀 PIPELINES",
            [
                ("neotron run basic", "Pipeline: Random Search"),
                ("neotron run adaptive", "Pipeline: Adaptive Multi-Strategy"),
                ("neotron run custom [config]", "Pipeline: Custom Composition"),
            ],
        ),
        (
            "🧪 TESTES",
            [
                ("neotron test unit", "Testes unitários (sem integração/benchmark)"),
                ("neotron test all", "Todos os testes"),
                ("neotron test coverage", "Testes com coverage HTML"),
                ("neotron test file <f>", "Arquivo de teste específico"),
                ("neotron test verify", "Verificação de integração completa"),
            ],
        ),
        (
            "🔍 QUALIDADE",
            [
                ("neotron check format", "Verificar formatação (black)"),
                ("neotron check lint", "Rodar linters (black+ruff+mypy)"),
                ("neotron check typecheck", "Type check (mypy)"),
                ("neotron check all", "Todos os checks de qualidade"),
                ("neotron format", "Formatar código (black+ruff fix)"),
            ],
        ),
        (
            "💰 CUSTOS",
            [
                ("neotron cost analysis <exp>", "Análise de custo de experimento"),
                ("neotron cost list", "Listar todos experimentos com custos"),
                ("neotron cost unified <exp>", "Relatório unificado (GPU + GCP credits)"),
                ("neotron cost credits", "Status de créditos CEREBRO GCP"),
                ("neotron cost limit <g> <c> <m>", "Definir limites de recursos"),
            ],
        ),
        (
            "📦 ML & ARTEFATOS",
            [
                ("neotron ml download <exp>", "Baixar melhor modelo do experimento"),
                ("neotron ml export <exp>", "Exportar resultados para CSV"),
                ("neotron ml dag <exp>", "Exportar definição DAG para PHANTOM"),
            ],
        ),
        (
            "📊 WORKFLOWS",
            [
                ("neotron workflow status <id>", "Status de workflow Temporal"),
                ("neotron workflow list", "Listar workflows em execução"),
                ("neotron workflow ray", "Status do cluster Ray"),
            ],
        ),
        (
            "❄️ NIX",
            [
                ("neotron nix shell", "Entrar no dev shell Nix"),
                ("neotron nix build", "Build do flake"),
                ("neotron nix update", "Atualizar inputs do flake"),
                ("neotron nix check", "Rodar flake checks"),
            ],
        ),
        (
            "🧹 HIGIENE",
            [
                ("neotron clean", "Limpar arquivos temporários"),
                ("neotron clean --all", "Limpeza nuclear (inclui volumes Docker)"),
            ],
        ),
        (
            "🛡️ SEGURANÇA",
            [
                ("neotron security scan [PATH]", "Scan completo: git hooks + Nix flake"),
                ("neotron security scan-git [PATH]", "Scan de hooks git maliciosos"),
                ("neotron security scan-flake [PATH]", "Scan de shellHook e fetchers suspeitos"),
            ],
        ),
        (
            "📡 SIEM EXPORT",
            [
                ("neotron siem status", "Status dos exportadores SIEM configurados"),
                (
                    "neotron siem export [--format FMT]",
                    "Exportar audit log para SIEM (cef/json/syslog)",
                ),
                ("neotron siem tail [--format FMT]", "Tail dos eventos sendo exportados"),
                ("neotron siem test [--target TGT]", "Testar conectividade com SIEM alvo"),
            ],
        ),
        (
            "🚀 QUICKSTART",
            [
                ("neotron quickstart", "Setup completo + pipeline básica"),
                ("neotron launch", "Lançar plataforma inteira (Neutron + Spectre)"),
            ],
        ),
    ]

    for title, commands in sections:
        click.secho(f"  {title}", fg="yellow", bold=True)
        for cmd, desc in commands:
            click.echo(f"    {click.style(cmd, fg='green', bold=True):<42} {desc}")
        click.echo()

    click.secho("═" * 62, fg="white", dim=True)
    click.secho(
        "  Use 'neotron <grupo> --help' para detalhes de cada subcomando", fg="bright_white"
    )
    click.secho("═" * 62, fg="white", dim=True)
    click.echo()


# ---------------------------------------------------------------------------
# Root CLI
# ---------------------------------------------------------------------------
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """
    \b
    NEXUS Platform — Enterprise-Grade AI Agent Orchestration
    Compliance-as-Code com Defense-in-Depth (4 camadas).

    Este é o ponto de entrada único. Todos os comandos do ecossistema
    (infra, worker, api, demos, pipelines, testes, custos, nix, etc.)
    estão disponíveis como subcomandos.
    """
    if ctx.invoked_subcommand is None:
        print_welcome()


# ============================================================================
# STATUS
# ============================================================================
@cli.command()
def status():
    """🔍 Mostrar estado do ambiente Nexus e dependências."""
    click.secho("\n🔍 NEXUS Environment Status\n", fg="blue", bold=True)

    deps = {
        "Temporal SDK": "temporalio",
        "FastAPI": "fastapi",
        "Pydantic": "pydantic",
        "Click": "click",
        "uvicorn": "uvicorn",
        "SQLAlchemy": "sqlalchemy",
    }
    for label, mod in deps.items():
        try:
            __import__(mod)
            click.echo(f"  {label:<22} {click.style('✅ Installed', fg='green')}")
        except ImportError:
            click.echo(f"  {label:<22} {click.style('❌ Missing', fg='red')}")

    try:
        from neutron.core.config import get_config

        config = get_config()
        click.secho("\n⚙️  Configuration:", fg="yellow", bold=True)
        click.echo(f"  API Host:        {config.api_host}:{config.api_port}")
        click.echo(f"  Primary LLM:     {config.llm.primary_provider.value}")
        click.echo(f"  Enabled LLMs:    {[p.value for p in config.llm.get_enabled_providers()]}")
        click.echo(
            f"  Smart Contracts: {'Enabled' if config.enable_smart_contracts else 'Disabled'}"
        )
    except ImportError:
        click.secho("  ⚠️  Core config unavailable (use 'uv run' or 'nix develop')", fg="yellow")
    except Exception as e:
        click.secho(f"  ❌ Config error: {e}", fg="red")

    click.echo()


@cli.command()
def features():
    """✨ Listar capacidades da plataforma (defense-in-depth)."""
    click.secho("\n✨ NEXUS Platform Features & Capabilities\n", fg="magenta", bold=True)

    layers = [
        (
            "🛡️  Layer 1: SENTINEL (Application)",
            "cyan",
            [
                "Python-level validation and business logic guards.",
                "GDPR/LGPD compliance checks on agent outputs.",
                "Pluggable policy engine (YAML/TOML-based rules).",
            ],
        ),
        (
            "🛡️  Layer 2: BASTION (Kernel)",
            "cyan",
            [
                "Kernel-level enforcement via seccomp-BPF.",
                "Syscall filtering prevents unauthorized data access.",
                "Namespace isolation per workflow execution context.",
            ],
        ),
        (
            "🛡️  Layer 3: BASTION-SC (Smart Contracts)",
            "cyan",
            [
                "On-chain compliance enforcement (Solidity/Sepolia).",
                "Automatic revert if consent/authorization missing.",
                "Integrated with DeFi protocols for audit trails.",
            ],
        ),
        (
            "🛡️  Layer 4: Audit Trail (Decentralized)",
            "cyan",
            [
                "Immutable audit logs on IPFS & Arweave.",
                "200+ year permanence for compliance tracking.",
                "Cryptographic proofs of execution integrity.",
            ],
        ),
        (
            "🧠 Orchestration & Agents",
            "green",
            [
                "Multi-agent swarm consensus (majority, unanimous, weighted).",
                "Temporal.io workflows for durable, fault-tolerant execution.",
                "Episodic memory with pgvector for context retention.",
            ],
        ),
        (
            "🔧 Developer Experience",
            "green",
            [
                "Reproducible builds via Nix flakes.",
                "Unified CLI (neotron) for all operations.",
                "Pre-commit hooks + CI/CD pipeline.",
            ],
        ),
    ]

    for title, color, items in layers:
        click.secho(title, fg=color, bold=True)
        for item in items:
            click.echo(f"    {item}")
        click.echo()


# ============================================================================
# INFRA
# ============================================================================
@cli.group()
def infra():
    """🏗️ Gerenciar infraestrutura (Temporal, MLflow, PostgreSQL, Ray)."""
    pass


@infra.command(name="up")
def infra_up():
    """Iniciar todos os serviços de infraestrutura."""
    click.secho("🚀 Starting infrastructure...", fg="cyan", bold=True)
    _run_docker_compose("up -d")
    click.echo("⏳ Waiting for services to be ready...")
    time.sleep(8)
    infra_status()
    click.secho("\n🌐 Access points:", fg="magenta", bold=True)
    click.echo("  • Temporal UI:    http://localhost:8088")
    click.echo("  • MLflow UI:      http://localhost:5000")
    click.echo("  • Ray Dashboard:  http://localhost:8265")
    click.echo("  • PostgreSQL:     localhost:5432")


@infra.command(name="down")
def infra_down():
    """Parar todos os serviços de infraestrutura."""
    click.secho("🛑 Stopping infrastructure...", fg="yellow", bold=True)
    _run_docker_compose("down")


@infra.command(name="status")
def infra_status():
    """Mostrar status dos containers Docker."""
    click.secho("📊 Infrastructure Status", fg="blue", bold=True)
    click.echo("═" * 50)
    _run_docker_compose("ps")


@infra.command(name="logs")
@click.argument("service", required=False)
def infra_logs(service):
    """Visualizar logs da infra (ou de um serviço específico)."""
    if service:
        click.secho(f"📋 Logs for {service}...", fg="cyan")
        _run_docker_compose(f"logs -f --tail=100 {service}")
    else:
        click.secho("📋 Infrastructure logs...", fg="cyan")
        _run_docker_compose("logs -f --tail=100")


@infra.command(name="restart")
@click.argument("service")
def infra_restart(service):
    """Reiniciar um serviço específico."""
    click.secho(f"🔄 Restarting {service}...", fg="yellow", bold=True)
    _run_docker_compose(f"restart {service}")


@infra.command(name="health")
def infra_health():
    """Health check de todos os endpoints."""
    click.secho("🏥 Running health checks...\n", fg="blue", bold=True)
    import urllib.error
    import urllib.request

    checks = [
        ("Temporal UI", "http://localhost:8088"),
        ("MLflow", "http://localhost:5000"),
        ("Ray Dashboard", "http://localhost:8265"),
        ("API (se rodando)", "http://localhost:8000/docs"),
    ]
    for name, url in checks:
        try:
            urllib.request.urlopen(url, timeout=3)
            click.echo(f"  {click.style('✓', fg='green')} {name}")
        except Exception:
            click.echo(f"  {click.style('✗', fg='red')} {name}")
    click.echo()


# ============================================================================
# WORKER
# ============================================================================
@cli.group()
def worker():
    """⚙️ Gerenciar Temporal Worker."""
    pass


@worker.command(name="start")
def worker_start():
    """Iniciar Temporal Worker (foreground, Ctrl+C para parar)."""
    click.secho("👷 Starting Temporal worker (foreground)...", fg="green", bold=True)
    click.secho("   Press Ctrl+C to stop", fg="yellow")
    _run_module("neutron.orchestration.worker")


@worker.command(name="bg")
def worker_bg():
    """Iniciar Worker em background."""
    click.secho("👷 Starting worker in background...", fg="green", bold=True)
    pid_file = PROJECT_ROOT / "worker.pid"
    log_file = PROJECT_ROOT / "worker.log"

    proc = subprocess.Popen(
        [sys.executable, "-m", "neutron.orchestration.worker"],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
        cwd=str(PROJECT_ROOT),
    )
    pid_file.write_text(str(proc.pid))
    click.secho(f"✅ Worker started (PID: {proc.pid})", fg="green")
    click.echo(f"   Logs: tail -f {log_file}")


@worker.command(name="stop")
def worker_stop():
    """Parar Worker em background."""
    pid_file = PROJECT_ROOT / "worker.pid"
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        click.secho(f"🛑 Stopping worker (PID: {pid})...", fg="yellow")
        try:
            os.kill(pid, 15)  # SIGTERM
            click.secho("✅ Worker stopped", fg="green")
        except ProcessLookupError:
            click.secho("⚠️  Worker was not running", fg="yellow")
        pid_file.unlink(missing_ok=True)
    else:
        click.secho("⚠️  No worker PID file found", fg="yellow")


@worker.command(name="logs")
def worker_logs():
    """Visualizar logs do worker."""
    log_file = PROJECT_ROOT / "worker.log"
    if log_file.exists():
        _run(f"tail -f {log_file}", shell=True)
    else:
        click.secho("⚠️  No worker log file found", fg="yellow")


# ============================================================================
# API / GUI / UI
# ============================================================================
@cli.command()
@click.option("--port", default=None, type=int, help="Override API port")
def api(port):
    """🌐 Iniciar servidor FastAPI."""
    click.secho("🌐 Starting Nexus API server...", fg="green", bold=True)
    try:
        from neutron.core.config import get_config

        config = get_config()
        target_port: int = port if port else config.api_port

        click.echo(f"API: http://{config.api_host}:{target_port}")
        click.echo(f"Docs: http://{config.api_host}:{target_port}/docs")

        import uvicorn

        uvicorn.run(
            "neutron.api.server:app",
            host=config.api_host,
            port=target_port,
            reload=True,
        )
    except ImportError as e:
        click.secho(f"❌ Import error: {e}", fg="red")
    except OSError as e:
        target_port = port or 8000
        if "Address already in use" in str(e):
            click.secho(f"❌ Port {target_port} is already in use.", fg="red")
            click.echo("   Use: neotron api --port 8001")
        else:
            click.secho(f"❌ {e}", fg="red")


@cli.command()
def gui():
    """🖥️ Iniciar interface GUI."""
    click.secho("🖥️ Starting Nexus GUI...", fg="green", bold=True)
    _run_module("neutron.gui.app")


@cli.command()
def ui():
    """🌐 Abrir todas as UIs no browser."""
    click.secho("🌐 Opening UIs...", fg="cyan")
    urls = [
        "http://localhost:8088",  # Temporal
        "http://localhost:5000",  # MLflow
        "http://localhost:8265",  # Ray
        "http://localhost:8000/docs",  # API docs
    ]
    for url in urls:
        click.echo(f"  → {url}")
        try:
            import webbrowser

            webbrowser.open(url)
        except Exception:
            pass


# ============================================================================
# DEMOS
# ============================================================================
@cli.group()
def demo():
    """🎮 Executar demos interativas do sistema."""
    pass


DEMO_SCRIPTS = {
    "phase2": "scripts/demo_phase2.py",
    "ingestion": "scripts/demo_document_ingestion.py",
    "bastion": "scripts/demo_bastion.py",
    "sentinel": "scripts/demo_sentinel.py",
    "nexus": "scripts/demo_nexus.py",
    "swarm": "neutron/scripts/demo_swarm.py",
    "cortex": "scripts/demo_cortex_live.py",
    "4layer": "scripts/demo_4layer.py",
}


def _make_demo_command(name: str, script: str, description: str):
    @click.command(name=name, help=description)
    def _cmd():
        run_script(script)

    return _cmd


for _name, _script in DEMO_SCRIPTS.items():
    _desc = f"Run {_name.replace('4layer', '4-Layer')} demo."
    demo.add_command(_make_demo_command(_name, _script, _desc))


@demo.command(name="list")
def demo_list():
    """Listar todas as demos disponíveis."""
    click.secho("\n🎮 Available Demos:\n", fg="blue", bold=True)
    demos = {
        **DEMO_SCRIPTS,
        "audit": "neutron/scripts/audit_compliance.py",
    }
    for name, path in sorted(demos.items()):
        click.echo(f"  • neotron demo {name:<14} ({path})")
    click.echo()


# ============================================================================
# RUN (Pipelines)
# ============================================================================
@cli.group()
def run():
    """🚀 Executar pipelines de ML."""
    pass


@run.command(name="basic")
def run_basic():
    """Pipeline: Random Search básica."""
    click.secho("🎯 Running basic random search pipeline...", fg="cyan", bold=True)
    _run_module_arg("neutron.cli.main", "1")


@run.command(name="adaptive")
def run_adaptive():
    """Pipeline: Adaptive Multi-Strategy."""
    click.secho("🧠 Running adaptive multi-strategy pipeline...", fg="magenta", bold=True)
    _run_module_arg("neutron.cli.main", "2")


@run.command(name="custom")
@click.argument("config_path", required=False)
def run_custom(config_path):
    """Pipeline: Custom Composition (com config JSON opcional)."""
    click.secho("🎨 Running custom composition pipeline...", fg="blue", bold=True)
    if config_path:
        _run_module_arg("neutron.cli.main", f"3 {config_path}")
    else:
        _run_module_arg("neutron.cli.main", "3")


# ============================================================================
# TEST
# ============================================================================
@cli.group()
def test():
    """🧪 Executar testes."""
    pass


@test.command(name="unit")
def test_unit():
    """Testes unitários (sem integração/benchmark)."""
    click.secho("🧪 Running unit tests...", fg="blue", bold=True)
    _run_pytest("-v -m 'not integration and not benchmark' --tb=short")


@test.command(name="all")
def test_all():
    """Todos os testes (inclui integração)."""
    click.secho("🧪 Running all tests...", fg="blue", bold=True)
    _run_pytest("-v --tb=short")


@test.command(name="coverage")
def test_coverage():
    """Testes com coverage HTML."""
    click.secho("📊 Running tests with coverage...", fg="blue", bold=True)
    _run_pytest("--cov=. --cov-report=html --cov-report=term")
    click.secho("Coverage report: htmlcov/index.html", fg="cyan")


@test.command(name="file")
@click.argument("file")
def test_file(file):
    """Executar arquivo de teste específico."""
    click.secho(f"🧪 Running {file}...", fg="blue", bold=True)
    _run_pytest(f"-v tests/{file}")


@test.command(name="verify")
def test_verify():
    """Verificação de integração completa."""
    click.secho("🔍 Running integration verification...", fg="blue", bold=True)
    run_script("scripts/verify_integration.py")


# ============================================================================
# CHECK (Quality)
# ============================================================================
@cli.group()
def check():
    """🔍 Verificar qualidade de código."""
    pass


@check.command(name="format")
def check_format():
    """Verificar formatação (black --check)."""
    click.secho("🔍 Checking formatting...", fg="blue", bold=True)
    _run("black --check .")


@check.command(name="lint")
def check_lint():
    """Rodar todos os linters (black, ruff, mypy)."""
    click.secho("🔍 Running linters...", fg="blue", bold=True)
    click.secho("→ Black", fg="yellow")
    _run("black --check .")
    click.secho("→ Ruff", fg="yellow")
    _run("ruff check .")
    click.secho("→ MyPy", fg="yellow")
    _run("mypy . --ignore-missing-imports", check=False)
    click.secho("✅ Linting complete", fg="green")


@check.command(name="typecheck")
def check_typecheck():
    """Type check com mypy."""
    click.secho("🔍 Type checking...", fg="blue", bold=True)
    _run("mypy . --ignore-missing-imports", check=False)


@check.command(name="all")
def check_all():
    """Todos os checks (format, lint, typecheck)."""
    check_format()
    check_lint()


@cli.command()
def format():
    """🎨 Formatar código (black + ruff fix)."""
    click.secho("🎨 Formatting code...", fg="magenta", bold=True)
    _run("black .")
    _run("ruff check --fix .")
    click.secho("✅ Code formatted", fg="green")


# ============================================================================
# COST
# ============================================================================
@cli.group()
def cost():
    """💰 Cost tracking e gestão de recursos."""
    pass


@cost.command(name="analysis")
@click.argument("experiment_name")
def cost_analysis(experiment_name):
    """Análise de custo de um experimento."""
    click.secho(f"💰 Cost Analysis: {experiment_name}", fg="cyan", bold=True)
    _run_module("neutron.integration.unified_cost_reporter", experiment_name)


@cost.command(name="list")
def cost_list():
    """Listar todos experimentos com uso de recursos."""
    click.secho("💰 All Experiments Resource Usage", fg="cyan", bold=True)
    _run_module("neutron.tracking.cost_tracker")


@cost.command(name="unified")
@click.argument("experiment_name")
@click.option("--days", default="7", help="Dias para análise (default: 7)")
def cost_unified(experiment_name, days):
    """Relatório unificado (GPU + GCP credits)."""
    click.secho(f"💰 Unified Cost Report: {experiment_name}", fg="cyan", bold=True)
    _run_module("neutron.integration.unified_cost_reporter", f"{experiment_name} --days {days}")


@cost.command(name="credits")
def cost_credits():
    """Status de créditos CEREBRO GCP."""
    click.secho("💳 CEREBRO GCP Credit Status", fg="cyan", bold=True)
    _run_module("neutron.tracking.cost_tracker")


@cost.command(name="limit")
@click.argument("gpu_count", type=int)
@click.argument("cpu_count", type=int)
@click.argument("memory_gb", type=int)
def cost_limit(gpu_count, cpu_count, memory_gb):
    """Definir limites de recursos para o próximo run."""
    click.secho("⚙️  Setting resource limits...", fg="yellow", bold=True)
    os.environ["MAX_GPUS"] = str(gpu_count)
    os.environ["MAX_CPUS"] = str(cpu_count)
    os.environ["MAX_MEMORY_GB"] = str(memory_gb)
    click.secho("✅ Limits set:", fg="green")
    click.echo(f"  • GPUs: {gpu_count}")
    click.echo(f"  • CPUs: {cpu_count}")
    click.echo(f"  • Memory: {memory_gb}GB")


# ============================================================================
# ML (Artifacts)
# ============================================================================
@cli.group()
def ml():
    """📦 Gerenciar artefatos de ML."""
    pass


@ml.command(name="download")
@click.argument("experiment_name")
@click.option("--output-dir", default="./best_model", help="Output directory")
def ml_download(experiment_name, output_dir):
    """Baixar melhor modelo do experimento."""
    click.secho(f"📦 Downloading best model from {experiment_name}...", fg="cyan", bold=True)
    _run_python_code(
        f"""
import mlflow
from pathlib import Path
mlflow.set_tracking_uri('http://localhost:5000')
experiment = mlflow.get_experiment_by_name('{experiment_name}')
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
best_run = runs.loc[runs['metrics.final_accuracy'].idxmax()]
client = mlflow.tracking.MlflowClient()
local_path = client.download_artifacts(best_run['run_id'], '', '{output_dir}')
print(f'Downloaded to: {{local_path}}')
print(f'Accuracy: {{best_run["metrics.final_accuracy"]:.4f}}')
"""
    )


@ml.command(name="export")
@click.argument("experiment_name")
@click.option("--output-file", default="results.csv", help="Output CSV file")
def ml_export(experiment_name, output_file):
    """Exportar resultados de experimento para CSV."""
    click.secho(f"📊 Exporting {experiment_name} to {output_file}...", fg="cyan", bold=True)
    _run_python_code(
        f"""
import mlflow
mlflow.set_tracking_uri('http://localhost:5000')
experiment = mlflow.get_experiment_by_name('{experiment_name}')
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
runs.to_csv('{output_file}', index=False)
print(f'Exported {{len(runs)}} runs to {output_file}')
"""
    )


@ml.command(name="dag")
@click.argument("experiment_name")
@click.option("--output-file", default="dag_tasks.json", help="Output JSON file")
def ml_dag(experiment_name, output_file):
    """Exportar definição DAG para PHANTOM."""
    click.secho(
        f"📋 Generating DAG task definition from {experiment_name}...", fg="cyan", bold=True
    )
    _run_python_code(
        f"""
import json, mlflow
mlflow.set_tracking_uri('http://localhost:5000')
experiment = mlflow.get_experiment_by_name('{experiment_name}')
runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
tasks = []
for _, run in runs.iterrows():
    tasks.append({{
        'task_id': f'train_{{run["run_id"]}}',
        'type': 'ml_training',
        'params': {{
            'learning_rate': run.get('params.learning_rate'),
            'batch_size': run.get('params.batch_size'),
        }},
        'metrics': {{
            'accuracy': run.get('metrics.final_accuracy'),
            'loss': run.get('metrics.final_loss'),
        }},
        'dependencies': [],
    }})
with open('{output_file}', 'w') as f:
    json.dump({{'tasks': tasks}}, f, indent=2)
print(f'Exported {{len(tasks)}} tasks to {output_file}')
"""
    )


# ============================================================================
# WORKFLOW
# ============================================================================
@cli.group()
def workflow():
    """📊 Monitorar workflows Temporal."""
    pass


@workflow.command(name="status")
@click.argument("workflow_id")
def workflow_status(workflow_id):
    """Status de um workflow específico."""
    click.secho(f"📊 Workflow Status: {workflow_id}", fg="cyan", bold=True)
    _run_python_code(
        f"""
import asyncio
from temporalio.client import Client

async def check():
    client = await Client.connect('localhost:7233')
    handle = client.get_workflow_handle('{workflow_id}')
    desc = await handle.describe()
    print(f'Status: {{desc.status}}')
    print(f'Start Time: {{desc.start_time}}')
    if desc.close_time:
        print(f'Duration: {{desc.close_time - desc.start_time}}')

asyncio.run(check())
"""
    )


@workflow.command(name="list")
def workflow_list():
    """Listar workflows em execução."""
    click.secho("📋 Running Workflows", fg="cyan", bold=True)
    _run_python_code(
        """
import asyncio
from temporalio.client import Client

async def list_workflows():
    client = await Client.connect('localhost:7233')
    async for wf in client.list_workflows('WorkflowExecutionStatus = "Running"'):
        print(f'{wf.id} - {wf.workflow_type}')

asyncio.run(list_workflows())
"""
    )


@workflow.command(name="ray")
def workflow_ray():
    """Status do cluster Ray."""
    click.secho("⚡ Ray Cluster Status", fg="cyan", bold=True)
    _run("ray status", check=False)


# ============================================================================
# NIX
# ============================================================================
@cli.group()
def nix():
    """❄️ Comandos do ecossistema Nix."""
    pass


@nix.command(name="shell")
def nix_shell():
    """Entrar no dev shell Nix."""
    click.secho("🐚 Entering Nix development shell...", fg="blue", bold=True)
    _run("nix develop")


@nix.command(name="build")
def nix_build():
    """Build do flake."""
    click.secho("🔨 Building Nix flake...", fg="blue", bold=True)
    _run("nix build")


@nix.command(name="update")
def nix_update():
    """Atualizar inputs do flake."""
    click.secho("⬆️  Updating flake inputs...", fg="blue", bold=True)
    _run("nix flake update")


@nix.command(name="check")
def nix_check():
    """Rodar flake checks."""
    click.secho("✅ Running flake checks...", fg="blue", bold=True)
    _run("nix flake check --no-build", check=False)


# ============================================================================
# CLEAN
# ============================================================================
@cli.command()
@click.option("--all", "clean_all", is_flag=True, help="Limpeza nuclear (inclui volumes Docker)")
def clean(clean_all):
    """🧹 Limpar arquivos temporários."""
    if clean_all:
        click.secho("🗑️  Nuclear cleanup (including Docker volumes)...", fg="red", bold=True)
        if click.confirm("Are you sure? This will delete all experiment data."):
            _run_docker_compose("down -v")
            click.secho("✅ Nuclear cleanup complete", fg="green")
        else:
            click.secho("Cancelled", fg="yellow")
        return

    click.secho("🧹 Cleaning temporary files...", fg="yellow", bold=True)
    for pattern in ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]:
        _run(f"find . -type d -name {pattern} -exec rm -rf {{}} + 2>/dev/null || true", shell=True)
    _run("find . -type f -name '*.pyc' -delete", shell=True)
    _run("find . -type f -name '.coverage' -delete", shell=True)
    for d in ["htmlcov", "dist", ".coverage"]:
        _run(f"rm -rf {d}", shell=True)
    for f in ["worker.log", "worker.pid"]:
        (PROJECT_ROOT / f).unlink(missing_ok=True)
    click.secho("✅ Cleanup complete", fg="green")


# ============================================================================
# BASTION
# ============================================================================
@cli.group()
def bastion():
    """🛡️ BASTION — Kernel-level enforcement via Landlock."""
    pass


@bastion.command(name="status")
def bastion_status():
    """Check Landlock availability and current enforcement status."""
    click.secho("\n🛡️  BASTION Landlock Status\n", fg="blue", bold=True)

    from neutron.bastion import LandlockEnforcer

    click.echo(f"  Kernel supports Landlock: {LandlockEnforcer.supported()}")
    if LandlockEnforcer.supported():
        click.echo(f"  ABI version:             {LandlockEnforcer.abi_version()}")
        click.echo(f"  NoNewPrivs set:          {LandlockEnforcer.check_no_new_privs()}")

        if not LandlockEnforcer.check_no_new_privs():
            click.secho(
                "\n  ⚠️  NoNewPrivs not set. Landlock enforcement requires:\n"
                "     • systemd: NoNewPrivileges=yes\n"
                "     • manual: setpriv --no-new-privs neotron ...\n",
                fg="yellow",
            )

    click.echo()


@bastion.command(name="profiles")
def bastion_profiles():
    """List available Landlock security profiles."""
    click.secho("\n🛡️  BASTION Security Profiles\n", fg="blue", bold=True)

    profiles = [
        ("readonly-data", "Read-only access to /data"),
        ("api-server", "API server: configs + logs, no exec"),
        ("agent-sandbox", "Tight sandbox: input/output dirs only"),
        ("compliance-auditor", "Read-only audit + data, write to audit log"),
    ]

    for name, desc in profiles:
        click.echo(f"  {click.style(name, fg='green', bold=True):<24} {desc}")
    click.echo()


# ============================================================================
# SECURITY
# ============================================================================
@cli.group()
def security():
    """🛡️ Security scanning — git hooks, Nix flakes, supply chain."""
    pass


@security.command(name="scan-git")
@click.argument("repo_path", required=False, default=".")
def security_scan_git(repo_path):
    """Scan a git repository for supply chain attack indicators.

    Detects:
    - Non-standard git hooks (post-checkout, post-commit, etc.)
    - Git config url.insteadOf redirects
    - Suspicious remotes
    - Malicious patterns in hook content
    - Uncommitted changes in critical files (flake.nix, etc.)

    Usage: neotron security scan-git [PATH]
    """
    click.secho(f"\n🛡️  Git Security Scan: {repo_path}\n", fg="blue", bold=True)

    from neutron.security.git_scanner import GitScanner

    scanner = GitScanner(repo_path)
    result = scanner.scan()

    if result.total_findings == 0:
        click.secho("✅ No suspicious findings.", fg="green", bold=True)
        return

    click.secho(f"⚠️  {result.total_findings} finding(s) encontrados:\n", fg="yellow", bold=True)

    for f in result.hooks_findings:
        color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "blue", "LOW": "white"}
        c = color.get(f.severity, "white")
        click.secho(f"  [{f.severity}] {f.category}: {f.path}", fg=c, bold=True)
        click.echo(f"    {f.description}")
        if f.evidence:
            click.secho(f"    Evidence: {f.evidence[:200]}", fg="white", dim=True)
        click.secho(f"    Fix: {f.remediation}", fg="green")
        click.echo()

    for f in result.config_findings:
        click.secho(f"  [{f.severity}] config: {f.key} = {f.value}", fg="red", bold=True)
        click.echo(f"    {f.description}")
        click.secho(f"    Fix: {f.remediation}", fg="green")
        click.echo()

    for f in result.remote_findings:
        click.secho(f"  [{f.severity}] remote: {f.key} = {f.value}", fg="yellow", bold=True)
        click.echo(f"    {f.description}")
        click.secho(f"    Fix: {f.remediation}", fg="green")
        click.echo()

    if result.has_critical:
        click.secho(
            "🔴 CRITICAL findings detected! Do NOT run nix develop/build.", fg="red", bold=True
        )
    else:
        click.secho("🟡 Review findings before proceeding.", fg="yellow")


@security.command(name="scan-flake")
@click.argument("flake_path", required=False, default="flake.nix")
def security_scan_flake(flake_path):
    """Scan a Nix flake for build-time injection indicators.

    Detects:
    - shellHook with suspicious commands (curl pipe, eval, /dev/tcp)
    - Unpinned fetchers (fetchGit without rev)
    - Suspicious flake inputs (non-GitHub URLs)
    - HOME/XDG redirections to project dirs

    Usage: neotron security scan-flake [PATH]
    """
    click.secho(f"\n🛡️  Flake Security Scan: {flake_path}\n", fg="blue", bold=True)

    from neutron.security.nix_checker import NixFlakeChecker

    checker = NixFlakeChecker(flake_path)
    result = checker.scan()

    if not result.findings:
        click.secho("✅ No suspicious findings in flake.", fg="green", bold=True)
        return

    click.secho(f"⚠️  {len(result.findings)} finding(s) encontrados:\n", fg="yellow", bold=True)

    for f in result.findings:
        color = {"CRITICAL": "red", "HIGH": "yellow", "MEDIUM": "blue", "LOW": "white"}
        c = color.get(f.severity, "white")
        click.secho(f"  [{f.severity}] {f.category}: {f.location}", fg=c, bold=True)
        click.echo(f"    {f.description}")
        if f.evidence:
            click.secho(f"    Evidence: {f.evidence[:200]}", fg="white", dim=True)
        click.secho(f"    Fix: {f.remediation}", fg="green")
        click.echo()

    if result.has_critical:
        click.secho("🔴 CRITICAL findings! Do NOT run nix develop.", fg="red", bold=True)
    else:
        click.secho("🟡 Review findings before building.", fg="yellow")


@security.command(name="scan")
@click.argument("path", required=False, default=".")
@click.option("--flake", "flake_path", default=None, help="Path to flake.nix")
def security_scan(path, flake_path):
    """Full security scan: git hooks + Nix flake.

    Runs both scan-git and scan-flake on the target.

    Usage: neotron security scan [PATH]
    """
    click.secho(f"\n🛡️  Full Security Scan: {path}\n", fg="blue", bold=True)
    click.secho("═" * 50, fg="white", dim=True)

    # Git scan
    click.secho("\n📁 Phase 1/2: Git Repository Scan\n", fg="cyan", bold=True)
    security_scan_git.callback(path)

    # Flake scan
    target_flake = flake_path or f"{path}/flake.nix"
    click.secho("\n❄️  Phase 2/2: Nix Flake Scan\n", fg="cyan", bold=True)
    security_scan_flake.callback(target_flake)

    click.secho("\n✅ Security scan complete.", fg="green", bold=True)


# ============================================================================
# QUICKSTART / LAUNCH
# ============================================================================
@cli.command()
def quickstart():
    """🚀 Setup completo: instalar + infra + pipeline básica."""
    click.secho("🚀 NEXUS Quickstart", fg="cyan", bold=True)
    click.secho("═" * 50, fg="white", dim=True)

    click.secho("\n[1/3] Installing dependencies...", fg="yellow")
    _run("uv sync")

    click.secho("\n[2/3] Starting infrastructure...", fg="yellow")
    infra_up()

    click.secho("\n[3/3] Running basic pipeline...", fg="yellow")
    run_basic()

    click.secho("\n" + "═" * 50, fg="green")
    click.secho("✅ Quickstart Complete!", fg="green", bold=True)
    click.secho("═" * 50, fg="green")
    click.echo()
    click.secho("Next steps:", fg="cyan")
    click.echo("  1. neotron worker bg        (iniciar worker em background)")
    click.echo("  2. neotron api               (subir API)")
    click.echo("  3. neotron ui                (abrir interfaces no browser)")
    click.echo()


@cli.command()
def launch():
    """🚀 Lançar plataforma inteira (Neutron API + Worker + Spectre Proxy)."""
    click.secho("🚀 Launching NEXUS Platform...", fg="cyan", bold=True)
    click.secho("═" * 50, fg="white", dim=True)

    script = PROJECT_ROOT / "scripts" / "launch_platform.sh"
    if script.exists():
        _run(f"bash {script}", shell=True)
    else:
        click.secho("❌ launch_platform.sh not found", fg="red")


# ============================================================================
# HELPER: run_script (existing, preserved for backward compat)
# ============================================================================
def run_script(path: str, use_module: bool = False):
    """Helper to run a Python script in the current env."""
    click.secho(f"▶️  Executing: {path}", fg="yellow")
    env = os.environ.copy()

    if use_module:
        module = path.replace("/", ".").replace(".py", "")
        cmd = [sys.executable, "-m", module]
    else:
        cmd = [sys.executable, str(PROJECT_ROOT / path)]

    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        click.secho(f"❌ Execution failed (exit {e.returncode})", fg="red", bold=True)
    except KeyboardInterrupt:
        click.secho("🛑 Interrupted by user", fg="yellow", bold=True)


# ============================================================================
# INTERNAL HELPERS
# ============================================================================
def _run(cmd: str, check: bool = True, shell: bool = False):
    """Run a shell command with output forwarding."""
    try:
        subprocess.run(cmd, shell=shell, check=check, cwd=str(PROJECT_ROOT))
    except subprocess.CalledProcessError:
        pass  # error already shown by subprocess
    except KeyboardInterrupt:
        click.secho("\n🛑 Interrupted", fg="yellow")


def _run_docker_compose(args: str):
    """Run docker-compose with given args."""
    _run(f"docker-compose {args}", shell=True)


def _run_module(module: str, extra_args: str = ""):
    """Run a Python module."""
    cmd = [sys.executable, "-m", module]
    if extra_args:
        cmd.extend(extra_args.split())
    try:
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)
    except subprocess.CalledProcessError:
        pass
    except KeyboardInterrupt:
        click.secho("\n🛑 Interrupted", fg="yellow")


def _run_module_arg(module: str, arg: str):
    """Run python -m <module> <arg>."""
    _run(f"{sys.executable} -m {module} {arg}", shell=True)


def _run_pytest(args: str):
    """Run pytest with given args."""
    _run(f"{sys.executable} -m pytest tests/ {args}", shell=True)


def _run_python_code(code: str):
    """Run inline Python code."""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    if proc.returncode != 0:
        click.secho(f"❌ Python code exited with {proc.returncode}", fg="red")


# ============================================================================
# NATS EVENT BRIDGE
# ============================================================================
cli.add_command(event_group)


# ============================================================================
# LICENSE VERIFICATION
# ============================================================================
@cli.group()
def license():
    """🔐 Verificar compliance de licenças via IP Guard.

    Integra com IP Guard (Rust) para verificar licenças de pacotes Nix
    contra a LicenseRegistry na blockchain.

    Modos:
      - Local: chama ip-guard via subprocess (precisa binário)
      - NATS:  envia request via NATS bridge para serviço remoto

    Cache: resultados são cacheados por 24h para evitar queries redundantes.
    """
    pass


@license.command(name="verify")
@click.argument("flake_path", type=click.Path(exists=True))
@click.option("--no-cache", is_flag=True, default=False, help="Ignorar cache e verificar novamente")
@click.option("--nats", "use_nats", is_flag=True, default=False, help="Usar NATS bridge (remoto)")
def license_verify(flake_path, no_cache, use_nats):
    """🔐 Verificar licença de um flake.nix.

    Exemplos:
      neotron license verify ./flake.nix
      neotron license verify ./flake.nix --no-cache
      neotron license verify ./flake.nix --nats
    """
    from pathlib import Path

    from neutron.license import verify

    flake = Path(flake_path).resolve()

    click.secho("\n🔐 Verifying license compliance...\n", fg="blue", bold=True)
    click.echo(f"  Flake: {flake}")

    if use_nats:
        click.echo("  Mode:  NATS bridge")
    else:
        click.echo("  Mode:  Local (ip-guard)")

    click.echo()

    try:
        result = verify(flake, use_cache=not no_cache)
    except FileNotFoundError as e:
        click.secho(f"❌ {e}", fg="red")
        return

    # Display results
    click.echo("📋 Package")
    click.echo(f"  Name:       {result.package_name}")
    click.echo(f"  Hash:       {result.package_hash}")
    click.echo(f"  SPDX:       {result.spdx_id}")
    click.echo()

    click.echo("🔍 Verification")
    if result.compliant:
        click.secho("  Status:     ✅ COMPLIANT", fg="green", bold=True)
    else:
        click.secho("  Status:     ❌ NON-COMPLIANT", fg="red", bold=True)

    if result.license_id:
        click.echo(f"  License ID: {result.license_id}")
    click.echo(f"  Source:     {result.source}")

    if result.errors:
        click.echo()
        click.secho("⚠️  Issues:", fg="yellow")
        for error in result.errors:
            click.echo(f"  • {error}")

    click.echo()
    if result.compliant:
        click.secho("✅ License compliance verified.", fg="green", bold=True)
    else:
        click.secho("❌ License compliance check failed.", fg="red", bold=True)


@license.command(name="status")
@click.option("--clear-cache", is_flag=True, default=False, help="Limpar cache de licenças")
def license_status(clear_cache):
    """🔐 Mostrar estado das licenças verificadas."""
    from neutron.license import LicenseCache, get_status

    if clear_cache:
        cache = LicenseCache()
        count = cache.clear()
        click.secho(f"✅ Cache cleared: {count} entries removed.", fg="green")
        return

    status = get_status()

    click.secho("\n🔐 License Verification Status\n", fg="blue", bold=True)

    click.echo(f"  Cached Verifications: {status['cached_verifications']}")
    click.secho(f"  Compliant:            {status['compliant']}", fg="green")
    if status["non_compliant"] > 0:
        click.secho(f"  Non-Compliant:        {status['non_compliant']}", fg="red")
    else:
        click.echo(f"  Non-Compliant:        {status['non_compliant']}")

    click.echo()
    if status["ip_guard_available"]:
        click.secho("  IP Guard:             ✅ Available", fg="green")
    else:
        click.secho("  IP Guard:             ❌ Not available", fg="red")

    click.echo(
        f"  NATS Bridge:          {'✅ Enabled' if status['nats_bridge_enabled'] else '⬜ Disabled'}"
    )
    click.echo(f"  Cache Dir:            {status['cache_dir']}")

    # List cached results
    if status["cached_verifications"] > 0:
        cache = LicenseCache()
        results = cache.list_all()
        click.echo()
        click.secho("📋 Cached Results:", fg="white", bold=True)
        for r in results[:10]:  # Show up to 10
            icon = "✅" if r.compliant else "❌"
            click.echo(
                f"  {icon} {r.package_name:<30} SPDX={r.spdx_id:<15} "
                f"{r.verified_at_formatted() if hasattr(r, 'verified_at_formatted') else ''}"
            )

    click.echo()


# ============================================================================
# SIEM EXPORT
# ============================================================================
@cli.group()
def siem():
    """📡 Exportar eventos de compliance para SIEM (CEF/JSON/Syslog).

    Suporta múltiplos formatos e alvos:
      - Formatos: cef (ArcSight/Splunk), leef (QRadar), json (Elastic/Owasaka), syslog (RFC 5424)
      - Alvos: file (para agentes Wazuh/Filebeat), syslog (UDP/TCP), nats (Owasaka SIEM)

    Configuração via variáveis de ambiente:
      NEUTRON_SIEM_DIR     Diretório de logs SIEM (default: /var/log/neotron/siem)
      NEUTRON_SYSLOG_HOST  Host do coletor syslog (default: localhost)
      NEUTRON_SYSLOG_PORT  Porta syslog (default: 514)
      NEUTRON_SYSLOG_PROTO Protocolo syslog (default: udp)
    """
    pass


@siem.command(name="status")
def siem_status():
    """📡 Mostrar estado dos exportadores SIEM configurados."""
    click.secho("\n📡 SIEM Export Status\n", fg="blue", bold=True)

    from neutron.siem.exporters import (
        DEFAULT_SIEM_LOG_DIR,
        DEFAULT_SYSLOG_HOST,
        DEFAULT_SYSLOG_PORT,
        DEFAULT_SYSLOG_PROTO,
    )

    # Directory status
    siem_dir = DEFAULT_SIEM_LOG_DIR
    click.echo(f"  Log Directory:     {siem_dir}")
    if siem_dir.exists():
        files = sorted(siem_dir.glob("*.log"))
        click.secho(f"  Status:            ✅ Exists ({len(files)} log files)", fg="green")
        for f in files[-5:]:
            size = f.stat().st_size
            click.echo(f"    └─ {f.name} ({size:,} bytes)")
    else:
        click.secho("  Status:            ⬜ Not created yet", fg="yellow")

    # Syslog config
    click.echo()
    click.echo(
        f"  Syslog Host:       {DEFAULT_SYSLOG_HOST}:{DEFAULT_SYSLOG_PORT}/{DEFAULT_SYSLOG_PROTO}"
    )

    # Test syslog connectivity
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    try:
        sock.sendto(b"", (DEFAULT_SYSLOG_HOST, DEFAULT_SYSLOG_PORT))
        click.secho("  Syslog Conn:       ✅ UDP socket ready", fg="green")
    except Exception as e:
        click.secho(f"  Syslog Conn:       ⚠️  {e}", fg="yellow")
    finally:
        sock.close()

    # NATS status
    try:
        from neutron.compliance.events import NATS_URL

        click.echo(f"  NATS URL:          {NATS_URL}")
        click.secho("  NATS Status:       ✅ Configured", fg="green")
    except ImportError:
        click.secho("  NATS Status:       ⚠️  nats-py not installed", fg="yellow")

    # In-memory audit log
    try:
        from neutron.compliance.audit_logger import AuditLogger

        audit = AuditLogger()
        all_events = audit.get_all()
        violations = audit.get_violations()
        click.echo()
        click.echo(f"  Audit Log Events:  {len(all_events)} total, {len(violations)} violations")
    except ImportError:
        click.secho("  Audit Log:         ⚠️  compliance module not loaded", fg="yellow")

    click.echo()


@siem.command(name="export")
@click.option("--format", "fmt", default="cef", help="Output format: cef, leef, json, syslog")
@click.option("--target", "target", default="file", help="Export target: file, syslog, nats")
@click.option("--syslog-host", default=None, help="Syslog collector host")
@click.option("--syslog-port", default=None, type=int, help="Syslog collector port")
def siem_export(fmt, target, syslog_host, syslog_port):
    """📡 Exportar audit log em memória para SIEM.

    Replay todos os eventos do audit log in-memory através do exportador
    SIEM no formato e alvo especificados.

    Exemplos:
      neotron siem export --format cef --target file
      neotron siem export --format json --target nats
      neotron siem export --format syslog --target syslog --syslog-host 10.0.0.1
    """
    from neutron.compliance.audit_logger import AuditLogger
    from neutron.siem.exporters import (
        DEFAULT_SIEM_LOG_DIR,
        DEFAULT_SYSLOG_HOST,
        DEFAULT_SYSLOG_PORT,
        SIEMExporter,
    )

    audit = AuditLogger()
    events = audit.get_all()

    if not events:
        click.secho("⚠️  Audit log is empty. Run compliance checks first.", fg="yellow")
        return

    click.secho(
        f"\n📡 Exporting {len(events)} events → format={fmt} target={target}\n",
        fg="blue",
        bold=True,
    )

    host = syslog_host or DEFAULT_SYSLOG_HOST
    port = syslog_port or DEFAULT_SYSLOG_PORT

    exporter = SIEMExporter(
        formats=[fmt],
        targets=[target],
        log_dir=DEFAULT_SIEM_LOG_DIR,
        syslog_host=host,
        syslog_port=port,
    )

    count = exporter.export_batch(events)
    exporter.close()

    click.secho(f"✅ Exported {count} events", fg="green", bold=True)

    if target == "file":
        date_str = __import__("time").strftime("%Y-%m-%d")
        filepath = DEFAULT_SIEM_LOG_DIR / f"neotron-{fmt}-{date_str}.log"
        click.echo(f"   Log file: {filepath}")
        # Show last 3 lines
        if filepath.exists():
            lines = filepath.read_text().splitlines()[-3:]
            click.echo()
            click.secho("   Preview (last 3 events):", fg="white", dim=True)
            for line in lines:
                click.echo(f"   {line[:120]}..." if len(line) > 120 else f"   {line}")


@siem.command(name="tail")
@click.option("--format", "fmt", default="json", help="Format to tail: cef, leef, json, syslog")
@click.option("--follow", "-f", is_flag=True, default=False, help="Follow mode (tail -f)")
@click.option("--lines", "-n", default=10, help="Number of lines to show")
def siem_tail(fmt, follow, lines):
    """📡 Visualizar eventos SIEM exportados (tail dos arquivos de log).

    Exemplos:
      neotron siem tail                    # últimos 10 eventos JSON
      neotron siem tail --format cef -n 20 # últimos 20 eventos CEF
      neotron siem tail -f                 # follow mode
    """
    from neutron.siem.exporters import DEFAULT_SIEM_LOG_DIR

    date_str = __import__("time").strftime("%Y-%m-%d")
    filepath = DEFAULT_SIEM_LOG_DIR / f"neotron-{fmt}-{date_str}.log"

    if not filepath.exists():
        click.secho(f"⚠️  No SIEM log file yet: {filepath}", fg="yellow")
        click.echo("   Run 'neotron siem export' first.")
        return

    if follow:
        click.secho(f"📡 Following {filepath} (Ctrl+C to stop)...\n", fg="blue", bold=True)
        try:
            with open(filepath) as f:
                f.seek(0, 2)  # end of file
                import time as _time

                while True:
                    line = f.readline()
                    if line:
                        click.echo(line.rstrip())
                    else:
                        _time.sleep(0.1)
        except KeyboardInterrupt:
            click.secho("\n🛑 Stopped", fg="yellow")
    else:
        click.secho(f"📡 Last {lines} lines of {filepath}:\n", fg="blue", bold=True)
        all_lines = filepath.read_text().splitlines()
        for line in all_lines[-lines:]:
            click.echo(line[:200] + "..." if len(line) > 200 else line)


@siem.command(name="test")
@click.option("--target", "target", default="file", help="Target to test: file, syslog, nats")
@click.option("--syslog-host", default=None, help="Syslog collector host")
@click.option("--syslog-port", default=None, type=int, help="Syslog collector port")
def siem_test(target, syslog_host, syslog_port):
    """📡 Testar conectividade com alvo SIEM.

    Envia um evento de teste para verificar se o pipeline está funcionando.

    Exemplos:
      neotron siem test --target file
      neotron siem test --target syslog --syslog-host 10.0.0.1
      neotron siem test --target nats
    """
    from neutron.siem.exporters import (
        DEFAULT_SIEM_LOG_DIR,
        DEFAULT_SYSLOG_HOST,
        DEFAULT_SYSLOG_PORT,
        SIEMExporter,
    )

    host = syslog_host or DEFAULT_SYSLOG_HOST
    port = syslog_port or DEFAULT_SYSLOG_PORT

    test_event = {
        "guardrail_name": "siem_test_event",
        "regulation": "TEST",
        "severity": "info",
        "passed": True,
        "audit_id": 0,
        "details": "SIEM connectivity test from neotron siem test",
        "timestamp": __import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
        "subject": "neotron.compliance.siem.test",
    }

    click.secho(f"\n📡 Testing SIEM export → target={target}\n", fg="blue", bold=True)

    exporter = SIEMExporter(
        formats=["json"],
        targets=[target],
        log_dir=DEFAULT_SIEM_LOG_DIR,
        syslog_host=host,
        syslog_port=port,
    )

    try:
        outputs = exporter.export(test_event)
        exporter.close()
        click.secho("✅ Test event exported successfully", fg="green", bold=True)
        for output in outputs:
            click.echo(f"   {output[:150]}..." if len(output) > 150 else f"   {output}")
    except Exception as e:
        click.secho(f"❌ Export failed: {e}", fg="red", bold=True)


# ============================================================================
# DEFI RISK MONITOR
# ============================================================================
@cli.group()
def defi():
    """📊 DeFi risk monitoring — posições, health factor, liquidações."""


@defi.command("risk")
@click.argument("loan_id")
@click.option("--contract", default=None, help="LendingProtocol address")
@click.option("--rpc-url", default="http://localhost:8545", show_default=True)
def defi_risk(loan_id: str, contract: str | None, rpc_url: str) -> None:
    """Avalia risco de uma posição on-chain e emite evento NATS se necessário."""
    import asyncio

    from neutron.defi.monitor import PositionMonitor

    _contract = contract or "0x0000000000000000000000000000000000000000"

    monitor = PositionMonitor(_contract, rpc_url)

    try:
        position = monitor.fetch_position(loan_id)
        click.secho(f"\n📊 Posição: {loan_id[:16]}...", fg="blue", bold=True)
        click.secho(f"   Borrower:      {position.borrower}", fg="cyan")
        click.secho(
            f"   Health Factor: {position.health_factor:.1f}%",
            fg={"healthy": "green", "warning": "yellow", "critical": "red"}.get(
                position.risk_level.value, "white"
            ),
        )
        click.secho(f"   LTV:           {position.ltv:.1%}", fg="cyan")
        click.secho(
            f"   Liquidatable:  {position.liquidatable}",
            fg="red" if position.liquidatable else "green",
        )
        click.secho(
            f"   Risk Level:    {position.risk_level.value.upper()}",
            fg={"healthy": "green", "warning": "yellow", "critical": "red"}.get(
                position.risk_level.value, "white"
            ),
            bold=True,
        )

        event = asyncio.run(monitor.evaluate(loan_id))
        if event:
            click.secho("\n⚠️  Evento emitido → neotron.defi.risk.v1", fg="yellow")
            click.secho(f"   Assessment: {event.assessment.get('output', '?')}", fg="cyan")
        else:
            click.secho("\n✅ Posição saudável — nenhum evento emitido", fg="green")
    except Exception as e:
        click.secho(f"❌ Erro: {e}", fg="red")
        raise SystemExit(1)


@defi.command("pool")
@click.option("--contract", default=None, help="LendingProtocol address")
@click.option("--rpc-url", default="http://localhost:8545", show_default=True)
def defi_pool(contract: str | None, rpc_url: str) -> None:
    """Mostra status atual do pool de liquidez."""
    from neutron.defi.monitor import PositionMonitor

    _contract = contract or "0x0000000000000000000000000000000000000000"
    monitor = PositionMonitor(_contract, rpc_url)

    try:
        pool = monitor.fetch_pool_status()
        click.secho("\n🏦 Pool Status", fg="blue", bold=True)
        for k, v in pool.items():
            click.secho(f"   {k}: {v}", fg="cyan")
    except Exception as e:
        click.secho(f"❌ Erro: {e}", fg="red")
        raise SystemExit(1)


# ============================================================================
# SUPPLY CHAIN (ROADMAP 2 — H3)
# ============================================================================
@cli.group()
def supply_chain():
    """⛓️  Supply chain compliance: SBOM, attestations, license registry."""


@supply_chain.command("sbom-generate")
@click.option(
    "--from-flake", "flake_path", default="flake.nix", show_default=True, help="Path to flake.nix"
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["cyclonedx", "spdx"]),
    default="cyclonedx",
    show_default=True,
)
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
def sbom_generate(flake_path: str, fmt: str, output: str | None) -> None:
    """Generate a Software Bill of Materials from a Nix flake."""
    import json
    import subprocess
    from pathlib import Path

    flake = Path(flake_path)
    if not flake.exists():
        click.secho(f"❌ {flake_path} not found", fg="red")
        raise SystemExit(1)

    click.secho(f"🔍 Parsing flake: {flake_path}", fg="blue")

    try:
        result = subprocess.run(
            ["nix", "eval", "--json", f"{flake.parent}#packages"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        packages = json.loads(result.stdout) if result.returncode == 0 else {}
    except Exception:
        packages = {}

    sbom = {
        "bomFormat": "CycloneDX" if fmt == "cyclonedx" else "SPDX",
        "specVersion": "1.5" if fmt == "cyclonedx" else "SPDX-2.3",
        "version": 1,
        "metadata": {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
            "component": {"name": flake.parent.name or "neotron", "type": "application"},
        },
        "components": [
            {"type": "library", "name": pkg, "bom-ref": f"pkg:{pkg}"} for pkg in packages.keys()
        ],
    }

    sbom_json = json.dumps(sbom, indent=2)

    if output:
        Path(output).write_text(sbom_json)
        click.secho(f"✅ SBOM written to {output}", fg="green")
    else:
        click.echo(sbom_json)


@supply_chain.command("attest-build")
@click.option("--flake", "flake_path", default="flake.nix", show_default=True)
@click.option(
    "--slsa-level", type=click.Choice(["0", "1", "2", "3"]), default="1", show_default=True
)
@click.option("--builder-id", default="neotron-ci", show_default=True)
def attest_build(flake_path: str, slsa_level: str, builder_id: str) -> None:
    """Generate a build attestation (SLSA provenance) for a Nix build."""
    import hashlib
    import json
    from pathlib import Path

    flake = Path(flake_path)
    flake_hash = hashlib.sha256(flake.read_bytes()).hexdigest() if flake.exists() else "unknown"

    attestation = {
        "_type": "https://in-toto.io/Statement/v0.1",
        "predicateType": "https://slsa.dev/provenance/v0.2",
        "subject": [{"name": flake.name, "digest": {"sha256": flake_hash}}],
        "predicate": {
            "builder": {"id": f"https://github.com/voidnxlabs/{builder_id}"},
            "buildType": "https://nixos.org/nix/flake",
            "invocation": {
                "configSource": {"uri": str(flake.absolute()), "digest": {"sha256": flake_hash}}
            },
            "metadata": {
                "buildStartedOn": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                "completeness": {"parameters": True, "environment": True, "materials": True},
            },
            "materials": [{"uri": str(flake.absolute()), "digest": {"sha256": flake_hash}}],
        },
        "slsaLevel": int(slsa_level),
    }

    click.echo(json.dumps(attestation, indent=2))
    click.secho(f"\n✅ SLSA Level {slsa_level} attestation generated", fg="green")


@supply_chain.command("verify")
@click.argument("component")
@click.option(
    "--rpc-url", default="http://localhost:8545", show_default=True, help="Ethereum RPC URL"
)
@click.option("--guardian-address", default=None, help="SupplyChainGuardian contract address")
def supply_chain_verify(component: str, rpc_url: str, guardian_address: str | None) -> None:
    """Verify a component's supply chain compliance status on-chain."""
    import subprocess

    if not guardian_address:
        click.secho(
            "⚠️  No --guardian-address provided. Pass the deployed SupplyChainGuardian address.",
            fg="yellow",
        )
        click.secho("    Deploy with: just contracts-deploy-local", fg="cyan")
        raise SystemExit(1)

    click.secho(f"🔍 Verifying supply chain for: {component}", fg="blue")
    click.secho(f"   RPC: {rpc_url}", fg="cyan")
    click.secho(f"   Guardian: {guardian_address}", fg="cyan")

    try:
        result = subprocess.run(
            [
                "cast",
                "call",
                guardian_address,
                "isCompliant(string)(bool)",
                component,
                "--rpc-url",
                rpc_url,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            status = result.stdout.strip()
            color = "green" if status == "true" else "red"
            icon = "✅" if status == "true" else "❌"
            click.secho(f"\n{icon} Compliant: {status}", fg=color, bold=True)
        else:
            click.secho(f"❌ cast call failed: {result.stderr}", fg="red")
    except FileNotFoundError:
        click.secho("⚠️  cast not found. Install Foundry: https://getfoundry.sh", fg="yellow")


# ============================================================================
# ENTRY POINT
# ============================================================================
def main():
    cli()


if __name__ == "__main__":
    main()
