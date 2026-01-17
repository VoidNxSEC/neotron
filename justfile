# justfile - Modern task runner (porque Make é vintage mas Just é chef's kiss)
# Filosofia: Commands should be discoverable, composable, and self-documenting

set shell := ["bash", "-uc"]
set dotenv-load := true

# Colors for pretty output
RED := '\033[0;31m'
GREEN := '\033[0;32m'
YELLOW := '\033[1;33m'
BLUE := '\033[0;34m'
PURPLE := '\033[0;35m'
CYAN := '\033[0;36m'
NC := '\033[0m' # No Color

# Default recipe - show help
default:
    @just --list --unsorted

# ============================================================================
# Setup & Installation
# ============================================================================

# Install all dependencies via Poetry
install:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📦 Installing Python dependencies via Poetry...{{NC}}"
    poetry install
    echo -e "{{GREEN}}✅ Dependencies installed{{NC}}"

# Setup Nix development environment
nix-shell:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🐚 Entering Nix development shell...{{NC}}"
    nix develop

# Build Nix flake
nix-build:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🔨 Building Nix flake...{{NC}}"
    nix build

# Update flake inputs
nix-update:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}⬆️  Updating flake inputs...{{NC}}"
    nix flake update

# ============================================================================
# Poetry Management
# ============================================================================

# Show Poetry environment info
poetry-info:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}📊 Poetry Environment{{NC}}"
    poetry env info
    echo ""
    echo -e "{{CYAN}}Installed packages:{{NC}}"
    poetry show --tree

# Update Poetry dependencies
poetry-update:
    #!/usr/bin/env bash
    echo -e "{{YELLOW}}⬆️  Updating Poetry dependencies...{{NC}}"
    poetry update
    echo ""
    echo -e "{{CYAN}}Outdated packages:{{NC}}"
    poetry show --outdated

# Add new dependency
poetry-add package:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}➕ Adding {{package}}...{{NC}}"
    poetry add {{package}}

# Add new dev dependency
poetry-add-dev package:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}➕ Adding {{package}} (dev)...{{NC}}"
    poetry add --group dev {{package}}

# Remove dependency
poetry-remove package:
    #!/usr/bin/env bash
    echo -e "{{RED}}➖ Removing {{package}}...{{NC}}"
    poetry remove {{package}}

# Export requirements.txt (para compatibilidade)
poetry-export:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📤 Exporting requirements.txt...{{NC}}"
    poetry export -f requirements.txt --output requirements.txt --without-hashes
    echo -e "{{GREEN}}✅ Exported to requirements.txt{{NC}}"

# ============================================================================
# Infrastructure Management
# ============================================================================

# Start all infrastructure services
infra-up:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}🚀 Starting infrastructure...{{NC}}"
    docker-compose up -d
    echo -e "{{YELLOW}}⏳ Waiting for services to be ready...{{NC}}"
    sleep 8
    just infra-status
    echo -e "{{GREEN}}✅ Infrastructure running{{NC}}"
    echo ""
    echo -e "{{PURPLE}}🌐 Access points:{{NC}}"
    echo -e "  • Temporal UI: {{CYAN}}http://localhost:8088{{NC}}"
    echo -e "  • MLflow UI:   {{CYAN}}http://localhost:5000{{NC}}"
    echo -e "  • Ray Dashboard: {{CYAN}}http://localhost:8265{{NC}}"

# Stop all infrastructure services
infra-down:
    #!/usr/bin/env bash
    echo -e "{{YELLOW}}🛑 Stopping infrastructure...{{NC}}"
    docker-compose down
    echo -e "{{GREEN}}✅ Infrastructure stopped{{NC}}"

# Show infrastructure status
infra-status:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}📊 Infrastructure Status{{NC}}"
    echo "════════════════════════════════════════════════════════════"
    docker-compose ps
    echo ""

# View infrastructure logs
infra-logs service="":
    #!/usr/bin/env bash
    if [ -z "{{service}}" ]; then
        docker-compose logs -f --tail=100
    else
        docker-compose logs -f --tail=100 {{service}}
    fi

# Restart specific service
infra-restart service:
    #!/usr/bin/env bash
    echo -e "{{YELLOW}}🔄 Restarting {{service}}...{{NC}}"
    docker-compose restart {{service}}

# Health check all services
infra-health:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🏥 Running health checks...{{NC}}"
    echo ""
    
    # Temporal
    if curl -s http://localhost:8088 > /dev/null 2>&1; then
        echo -e "{{GREEN}}✓{{NC}} Temporal UI"
    else
        echo -e "{{RED}}✗{{NC}} Temporal UI"
    fi
    
    # MLflow
    if curl -s http://localhost:5000 > /dev/null 2>&1; then
        echo -e "{{GREEN}}✓{{NC}} MLflow"
    else
        echo -e "{{RED}}✗{{NC}} MLflow"
    fi
    
    # PostgreSQL
    if docker-compose exec -T postgres pg_isready > /dev/null 2>&1; then
        echo -e "{{GREEN}}✓{{NC}} PostgreSQL"
    else
        echo -e "{{RED}}✗{{NC}} PostgreSQL"
    fi

# ============================================================================
# Worker Management
# ============================================================================

# Start Temporal worker (blocking)
worker:
    #!/usr/bin/env bash
    echo -e "{{PURPLE}}👷 Starting Temporal worker...{{NC}}"
    echo -e "{{YELLOW}}Press Ctrl+C to stop{{NC}}"
    python -m neutron.orchestration.worker

# Start worker in background
worker-bg:
    #!/usr/bin/env bash
    echo -e "{{PURPLE}}👷 Starting worker in background...{{NC}}"
    nohup python -m neutron.orchestration.worker > worker.log 2>&1 &
    echo $! > worker.pid
    echo -e "{{GREEN}}✅ Worker started (PID: $(cat worker.pid)){{NC}}"
    echo -e "{{CYAN}}Logs: tail -f worker.log{{NC}}"

# Stop background worker
worker-stop:
    #!/usr/bin/env bash
    if [ -f worker.pid ]; then
        PID=$(cat worker.pid)
        echo -e "{{YELLOW}}🛑 Stopping worker (PID: $PID)...{{NC}}"
        kill $PID 2>/dev/null || echo -e "{{RED}}Worker not running{{NC}}"
        rm worker.pid
    else
        echo -e "{{YELLOW}}No worker PID file found{{NC}}"
    fi

# View worker logs
worker-logs:
    tail -f worker.log

# ============================================================================
# Pipeline Execution
# ============================================================================

# Run basic random search pipeline
run-basic:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}🎯 Running basic random search pipeline...{{NC}}"
    python -m neutron.cli.main 1

# Run adaptive multi-strategy pipeline
run-adaptive:
    #!/usr/bin/env bash
    echo -e "{{PURPLE}}🧠 Running adaptive multi-strategy pipeline...{{NC}}"
    python -m neutron.cli.main 2

# Run custom composition pipeline
run-custom:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🎨 Running custom composition pipeline...{{NC}}"
    python -m neutron.cli.main 3

# Run pipeline with custom config
run config_path:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}🚀 Running pipeline with config: {{config_path}}{{NC}}"
    python -c "
    import asyncio
    from pathlib import Path
    import json
    from neutron.core.models import PipelineConfig
    from neutron.orchestration.workflows import start_adaptive_pipeline

    config_dict = json.loads(Path('{{config_path}}').read_text())
    config = PipelineConfig(**config_dict)
    asyncio.run(start_adaptive_pipeline(config))
    "

# ============================================================================
# Cost Tracking & Resource Management
# ============================================================================

# Show cost analysis for experiment
cost-analysis experiment_name:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}💰 Cost Analysis: {{experiment_name}}{{NC}}"
    python -c "
    import mlflow
    from datetime import datetime
    
    mlflow.set_tracking_uri('http://localhost:5000')
    experiment = mlflow.get_experiment_by_name('{{experiment_name}}')
    
    if not experiment:
        print('Experiment not found')
        exit(1)
    
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    
    if runs.empty:
        print('No runs found')
        exit(1)
    
    # Cost calculation (ajusta com seus pricing)
    GPU_COST_PER_HOUR = 0.90  # A100 pricing example
    CPU_COST_PER_HOUR = 0.05
    
    total_gpu_hours = runs['metrics.training_time'].sum() / 3600 if 'metrics.training_time' in runs else 0
    total_cost = total_gpu_hours * GPU_COST_PER_HOUR
    
    print(f'')
    print(f'Total Runs: {len(runs)}')
    print(f'Total GPU Hours: {total_gpu_hours:.2f}h')
    print(f'Estimated Cost: \${total_cost:.2f}')
    print(f'')
    print(f'Best Accuracy: {runs[\"metrics.final_accuracy\"].max():.4f}')
    print(f'Cost per 1% Accuracy: \${total_cost / (runs[\"metrics.final_accuracy\"].max() * 100):.3f}')
    print(f'')
    print(f'💡 Top 3 Most Efficient Runs (accuracy/cost):')
    runs['efficiency'] = runs['metrics.final_accuracy'] / (runs['metrics.training_time'] / 3600 * GPU_COST_PER_HOUR)
    top_runs = runs.nlargest(3, 'efficiency')[['run_id', 'metrics.final_accuracy', 'metrics.training_time', 'efficiency']]
    print(top_runs.to_string(index=False))
    "

# List all experiments with resource usage
cost-list:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}💰 All Experiments Resource Usage{{NC}}"
    python -c "
    import mlflow
    import pandas as pd
    
    mlflow.set_tracking_uri('http://localhost:5000')
    experiments = mlflow.search_experiments()
    
    data = []
    for exp in experiments:
        runs = mlflow.search_runs(experiment_ids=[exp.experiment_id])
        if not runs.empty:
            gpu_hours = runs['metrics.training_time'].sum() / 3600 if 'metrics.training_time' in runs else 0
            data.append({
                'Experiment': exp.name,
                'Runs': len(runs),
                'GPU Hours': f'{gpu_hours:.2f}h',
                'Est. Cost': f'\${gpu_hours * 0.90:.2f}',
                'Best Acc': f'{runs[\"metrics.final_accuracy\"].max():.4f}' if 'metrics.final_accuracy' in runs else 'N/A'
            })
    
    df = pd.DataFrame(data)
    print(df.to_string(index=False))
    "

# Set resource limits for next run
resource-limit gpu_count cpu_count memory_gb:
    #!/usr/bin/env bash
    echo -e "{{YELLOW}}⚙️  Setting resource limits...{{NC}}"
    export MAX_GPUS={{gpu_count}}
    export MAX_CPUS={{cpu_count}}
    export MAX_MEMORY_GB={{memory_gb}}
    echo -e "{{GREEN}}✅ Limits set:{{NC}}"
    echo -e "  • GPUs: {{gpu_count}}"
    echo -e "  • CPUs: {{cpu_count}}"
    echo -e "  • Memory: {{memory_gb}}GB"

# ============================================================================
# Development & Testing
# ============================================================================

# Run unit tests
test:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🧪 Running unit tests...{{NC}}"
    pytest tests/ -v -m "not integration and not benchmark" --tb=short

# Run all tests including integration
test-all:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🧪 Running all tests...{{NC}}"
    pytest tests/ -v --tb=short

# Run tests with coverage
test-coverage:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}📊 Running tests with coverage...{{NC}}"
    pytest tests/ --cov=. --cov-report=html --cov-report=term
    echo -e "{{CYAN}}Coverage report: htmlcov/index.html{{NC}}"

# Run specific test file
test-file file:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🧪 Running {{file}}...{{NC}}"
    pytest tests/{{file}} -v

# Format code with black and ruff
fmt:
    #!/usr/bin/env bash
    echo -e "{{PURPLE}}🎨 Formatting code...{{NC}}"
    black .
    ruff check --fix .
    echo -e "{{GREEN}}✅ Code formatted{{NC}}"

# Run linters
lint:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🔍 Running linters...{{NC}}"
    echo -e "{{YELLOW}}→ Black{{NC}}"
    black --check .
    echo -e "{{YELLOW}}→ Ruff{{NC}}"
    ruff check .
    echo -e "{{YELLOW}}→ MyPy{{NC}}"
    mypy . --ignore-missing-imports || true
    echo -e "{{GREEN}}✅ Linting complete{{NC}}"

# Type check with mypy
typecheck:
    #!/usr/bin/env bash
    echo -e "{{BLUE}}🔍 Type checking...{{NC}}"
    mypy . --ignore-missing-imports

# ============================================================================
# Monitoring & Debugging
# ============================================================================

# Open all UIs in browser
ui:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}🌐 Opening UIs...{{NC}}"
    if command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:8088 &  # Temporal
        xdg-open http://localhost:5000 &  # MLflow
        xdg-open http://localhost:8265 &  # Ray
    elif command -v open &> /dev/null; then
        open http://localhost:8088
        open http://localhost:5000
        open http://localhost:8265
    else
        echo -e "{{YELLOW}}Manual access:{{NC}}"
        echo "  Temporal: http://localhost:8088"
        echo "  MLflow:   http://localhost:5000"
        echo "  Ray:      http://localhost:8265"
    fi

# Query workflow status
workflow-status workflow_id:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📊 Workflow Status: {{workflow_id}}{{NC}}"
    python -c "
    import asyncio
    from temporalio.client import Client
    
    async def check():
        client = await Client.connect('localhost:7233')
        handle = client.get_workflow_handle('{{workflow_id}}')
        desc = await handle.describe()
        print(f'Status: {desc.status}')
        print(f'Start Time: {desc.start_time}')
        if desc.close_time:
            print(f'Duration: {desc.close_time - desc.start_time}')
    
    asyncio.run(check())
    "

# List running workflows
workflow-list:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📋 Running Workflows{{NC}}"
    python -c "
    import asyncio
    from temporalio.client import Client
    
    async def list_workflows():
        client = await Client.connect('localhost:7233')
        async for workflow in client.list_workflows('WorkflowExecutionStatus = \"Running\"'):
            print(f'{workflow.id} - {workflow.workflow_type}')
    
    asyncio.run(list_workflows())
    "

# Ray cluster status
ray-status:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}⚡ Ray Cluster Status{{NC}}"
    ray status || echo -e "{{YELLOW}}Ray not initialized{{NC}}"

# ============================================================================
# Data & Artifacts Management
# ============================================================================

# Download best model from experiment
download-best experiment_name output_dir="./best_model":
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📦 Downloading best model from {{experiment_name}}...{{NC}}"
    python -c "
    import mlflow
    from pathlib import Path
    
    mlflow.set_tracking_uri('http://localhost:5000')
    experiment = mlflow.get_experiment_by_name('{{experiment_name}}')
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    best_run = runs.loc[runs['metrics.final_accuracy'].idxmax()]
    
    # Download artifacts
    client = mlflow.tracking.MlflowClient()
    local_path = client.download_artifacts(best_run['run_id'], '', '{{output_dir}}')
    
    print(f'Downloaded to: {local_path}')
    print(f'Accuracy: {best_run[\"metrics.final_accuracy\"]:.4f}')
    "

# Export experiment results to CSV
export-results experiment_name output_file="results.csv":
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📊 Exporting {{experiment_name}} to {{output_file}}...{{NC}}"
    python -c "
    import mlflow
    
    mlflow.set_tracking_uri('http://localhost:5000')
    experiment = mlflow.get_experiment_by_name('{{experiment_name}}')
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    runs.to_csv('{{output_file}}', index=False)
    
    print(f'Exported {len(runs)} runs to {{output_file}}')
    "

# ============================================================================
# Cleanup
# ============================================================================

# Clean temporary files
clean:
    #!/usr/bin/env bash
    echo -e "{{YELLOW}}🧹 Cleaning temporary files...{{NC}}"
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete
    rm -rf htmlcov/
    rm -rf .coverage
    rm -rf /tmp/ray
    rm -f worker.log worker.pid
    echo -e "{{GREEN}}✅ Cleanup complete{{NC}}"

# Nuclear clean - remove everything including Docker volumes
clean-all: clean
    #!/usr/bin/env bash
    echo -e "{{RED}}🗑️  Nuclear cleanup (including Docker volumes)...{{NC}}"
    read -p "Are you sure? This will delete all experiment data [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v
        rm -rf /tmp/sentiment_dataset
        echo -e "{{GREEN}}✅ Nuclear cleanup complete{{NC}}"
    else
        echo -e "{{YELLOW}}Cancelled{{NC}}"
    fi

# ============================================================================
# Unified Cost Reporting (Neutron + CEREBRO)
# ============================================================================

# Unified cost report (Neutron GPU + CEREBRO GCP credits)
cost-unified experiment_name days="7":
    #!/usr/bin/env bash
    echo -e "{{CYAN}}💰 Unified Cost Report (Neutron + CEREBRO){{NC}}"
    python -m neutron.integration.unified_cost_reporter "{{experiment_name}}" --days {{days}}

# Quick credit status check
credits-status:
    #!/usr/bin/env bash
    echo -e "{{CYAN}}💳 CEREBRO GCP Credit Status{{NC}}"
    python -c "
    from neutron.tracking.cost_tracker import CerebroCreditValidator
    validator = CerebroCreditValidator()
    status = validator.get_credit_status(days_back=7)

    if 'error' in status:
        print(f'Error: {status[\"error\"]}')
    else:
        print(f'')
        print(f'Total Credits: \${status[\"total_credits\"]:.2f}')
        print(f'Credits Used: \${status[\"credits_used\"]:.2f} ({status[\"percentage_used\"]:.1f}%)')
        print(f'Credits Remaining: \${status[\"credits_remaining\"]:.2f} ({status[\"percentage_remaining\"]:.1f}%)')
        print(f'Burn Rate: \${status[\"burn_rate_per_day\"]:.2f}/day')
        print(f'Days Until Exhausted: {status[\"days_until_exhausted\"]:.0f}' if status['days_until_exhausted'] != float('inf') else 'Days Until Exhausted: ∞')
        print(f'')
    "

# ============================================================================
# Integration Helpers (para DAG systems como PHANTOM)
# ============================================================================

# Generate DAG-compatible task definition
dag-export experiment_name output_file="dag_tasks.json":
    #!/usr/bin/env bash
    echo -e "{{CYAN}}📋 Generating DAG task definition...{{NC}}"
    python -c "
    import json
    import mlflow
    
    mlflow.set_tracking_uri('http://localhost:5000')
    experiment = mlflow.get_experiment_by_name('{{experiment_name}}')
    runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
    
    # Convert to DAG-compatible format
    tasks = []
    for _, run in runs.iterrows():
        task = {
            'task_id': f'train_{run[\"run_id\"]}',
            'type': 'ml_training',
            'params': {
                'learning_rate': run.get('params.learning_rate'),
                'batch_size': run.get('params.batch_size'),
                'num_epochs': run.get('params.num_epochs'),
            },
            'metrics': {
                'accuracy': run.get('metrics.final_accuracy'),
                'loss': run.get('metrics.final_loss'),
                'training_time': run.get('metrics.training_time'),
            },
            'dependencies': [],  # Customize conforme seu DAG
        }
        tasks.append(task)
    
    with open('{{output_file}}', 'w') as f:
        json.dump({'tasks': tasks}, f, indent=2)
    
    print(f'Exported {len(tasks)} tasks to {{output_file}}')
    "

# ============================================================================
# Quick Start Combo
# ============================================================================

# Complete setup and run basic pipeline
quickstart: install infra-up
    #!/usr/bin/env bash
    echo ""
    echo -e "{{GREEN}}════════════════════════════════════════════════════════════{{NC}}"
    echo -e "{{GREEN}}  ✅ Quick Start Complete!{{NC}}"
    echo -e "{{GREEN}}════════════════════════════════════════════════════════════{{NC}}"
    echo ""
    echo -e "{{CYAN}}Next steps:{{NC}}"
    echo -e "  {{PURPLE}}1.{{NC}} just worker-bg     {{YELLOW}}# Start worker in background{{NC}}"
    echo -e "  {{PURPLE}}2.{{NC}} just run-basic     {{YELLOW}}# Run basic pipeline{{NC}}"
    echo ""
    echo -e "{{CYAN}}Or run adaptive:{{NC}}"
    echo -e "  just run-adaptive"
    echo ""
    echo -e "{{CYAN}}Monitor:{{NC}}"
    echo -e "  just ui               {{YELLOW}}# Open all dashboards{{NC}}"
    echo -e "  just cost-analysis <experiment_name>"
    echo ""
