# Makefile - Because typing long commands is for chumps
# Filosofia: Automation beats repetition

.PHONY: help install start-infra stop-infra worker run-basic run-adaptive test clean

# Default target
help:
	@echo "════════════════════════════════════════════════════════════"
	@echo "  Adaptive ML Pipeline - Temporal + Ray + MLflow"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make install        Install all dependencies"
	@echo "  make start-infra    Start Temporal + MLflow + PostgreSQL"
	@echo "  make stop-infra     Stop all infrastructure"
	@echo ""
	@echo "Run Commands:"
	@echo "  make worker         Start Temporal worker"
	@echo "  make run-basic      Run basic random search pipeline"
	@echo "  make run-adaptive   Run adaptive multi-strategy pipeline"
	@echo "  make run-custom     Run custom composition pipeline"
	@echo ""
	@echo "Development:"
	@echo "  make test           Run unit tests"
	@echo "  make test-all       Run all tests (including integration)"
	@echo "  make lint           Run linters (black + ruff)"
	@echo "  make format         Format code with black"
	@echo ""
	@echo "Monitoring:"
	@echo "  make logs           Show infrastructure logs"
	@echo "  make status         Show system status"
	@echo "  make ui             Open all UIs in browser"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean          Clean temporary files"
	@echo "  make clean-all      Clean everything (including docker volumes)"
	@echo ""
	@echo "════════════════════════════════════════════════════════════"

# ============================================================================
# Setup
# ============================================================================

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

start-infra:
	@echo "🚀 Starting infrastructure (Temporal + MLflow + PostgreSQL)..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo "✅ Infrastructure running"
	@echo ""
	@echo "🌐 Access points:"
	@echo "  - Temporal UI: http://localhost:8088"
	@echo "  - MLflow UI:   http://localhost:5000"
	@echo "  - PostgreSQL:  localhost:5432"
	@echo ""

stop-infra:
	@echo "🛑 Stopping infrastructure..."
	docker-compose down
	@echo "✅ Infrastructure stopped"

# ============================================================================
# Run
# ============================================================================

worker:
	@echo "👷 Starting Temporal worker..."
	@echo "Press Ctrl+C to stop"
	python worker.py

run-basic:
	@echo "🎯 Running basic random search pipeline..."
	python main.py 1

run-adaptive:
	@echo "🧠 Running adaptive multi-strategy pipeline..."
	python main.py 2

run-custom:
	@echo "🎨 Running custom composition pipeline..."
	python main.py 3

# ============================================================================
# Development
# ============================================================================

test:
	@echo "🧪 Running unit tests..."
	pytest tests/ -v -m "not integration and not benchmark" --tb=short

test-all:
	@echo "🧪 Running all tests (including integration)..."
	pytest tests/ -v --tb=short

test-coverage:
	@echo "📊 Running tests with coverage..."
	pytest tests/ --cov=. --cov-report=html --cov-report=term

lint:
	@echo "🔍 Running linters..."
	@echo "→ Black..."
	black --check .
	@echo "→ Ruff..."
	ruff check .
	@echo "→ MyPy..."
	mypy . --ignore-missing-imports
	@echo "✅ Linting complete"

format:
	@echo "🎨 Formatting code..."
	black .
	ruff check --fix .
	@echo "✅ Code formatted"

# ============================================================================
# Monitoring
# ============================================================================

logs:
	@echo "📋 Showing infrastructure logs..."
	docker-compose logs -f

status:
	@echo "📊 System Status"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Docker Containers:"
	@docker-compose ps
	@echo ""
	@echo "Ray Cluster:"
	@ray status 2>/dev/null || echo "  Ray not initialized (run make worker first)"
	@echo ""

ui:
	@echo "🌐 Opening UIs in browser..."
	@which open >/dev/null 2>&1 && open http://localhost:8088 || echo "Temporal UI: http://localhost:8088"
	@which open >/dev/null 2>&1 && open http://localhost:5000 || echo "MLflow UI: http://localhost:5000"

# ============================================================================
# Cleanup
# ============================================================================

clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf /tmp/ray
	@echo "✅ Cleanup complete"

clean-all: clean
	@echo "🗑️  Cleaning everything (including Docker volumes)..."
	docker-compose down -v
	@echo "✅ Full cleanup complete"

# ============================================================================
# Development Utilities
# ============================================================================

shell:
	@echo "🐚 Starting IPython shell with imports..."
	ipython -i -c "from models import *; from optimizer import *; from workflows import *; print('Imports loaded. Ready to experiment.')"

notebook:
	@echo "📓 Starting Jupyter notebook..."
	jupyter notebook

# ============================================================================
# Quick Start
# ============================================================================

quickstart: install start-infra
	@echo ""
	@echo "════════════════════════════════════════════════════════════"
	@echo "  ✅ Quick Start Complete!"
	@echo "════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Terminal 1: make worker"
	@echo "  2. Terminal 2: make run-basic"
	@echo ""
	@echo "Or run adaptive pipeline:"
	@echo "  make run-adaptive"
	@echo ""
	@echo "Monitor at:"
	@echo "  - Temporal UI: http://localhost:8088"
	@echo "  - MLflow UI:   http://localhost:5000"
	@echo ""
