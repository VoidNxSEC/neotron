#!/usr/bin/env python3
"""
Neutron ML Pipeline - CLI Interface

Usage:
    python main.py 1                    # Basic random search
    python main.py 2                    # Adaptive multi-strategy
    python main.py 3                    # Custom multi-phase
    python main.py --config config.json # Custom config file

Examples from README:
    - Mode 1: Basic random search (20 trials, 4 parallel)
    - Mode 2: Adaptive strategy evolution (GRID → RANDOM → BAYESIAN → EVOLUTIONARY)
    - Mode 3: Custom multi-phase (quick exploration → focused search)
"""
import asyncio
import sys
import argparse
import json
from pathlib import Path
from typing import Optional

from neutron.core.models import (
    PipelineConfig,
    HyperparameterSpace,
    SearchStrategy
)
from neutron.orchestration.workflows import start_adaptive_pipeline


# ============================================================================
# Example Pipelines
# ============================================================================

async def run_basic(dataset_path: str = "imdb") -> str:
    """
    Example 1: Basic Random Search

    Perfect for:
    - Quick baseline
    - Initial exploration
    - When you don't know the space well

    Config:
    - 20 trials total
    - 4 parallel at a time
    - Pure random sampling
    """

    print("="*80)
    print("  🎲 Mode 1: Basic Random Search")
    print("="*80)
    print("")
    print("Strategy: RANDOM")
    print("Trials: 20")
    print("Parallel: 4")
    print("")

    config = PipelineConfig(
        experiment_name="basic_random_search",
        dataset_path=dataset_path,
        initial_strategy=SearchStrategy.RANDOM,
        hyperparameter_space=HyperparameterSpace(),  # Default space
        max_trials=20,
        max_parallel_trials=4,
        patience=15,  # Early stop se não melhora
        min_improvement=0.01
    )

    workflow_id = await start_adaptive_pipeline(config)

    print("")
    print("✅ Workflow started!")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   Temporal UI: http://localhost:8088/namespaces/default/workflows/{workflow_id}")
    print(f"   MLflow UI:   http://localhost:5000/#/experiments")
    print("")

    return workflow_id


async def run_adaptive(dataset_path: str = "imdb") -> str:
    """
    Example 2: Adaptive Multi-Strategy

    Perfect for:
    - Longer searches
    - Unknown optimal region
    - Want automatic strategy evolution

    Behavior:
    - Starts with GRID (systematic)
    - Switches to RANDOM if stagnant (10 trials no improvement)
    - Switches to BAYESIAN if improvement detected
    - Switches to EVOLUTIONARY for final exploration

    Config:
    - 50 trials total
    - Auto-adapts strategy based on performance
    - Patience: 10 trials
    """

    print("="*80)
    print("  🧠 Mode 2: Adaptive Multi-Strategy")
    print("="*80)
    print("")
    print("Strategy: GRID → RANDOM → BAYESIAN → EVOLUTIONARY (adaptive)")
    print("Trials: 50")
    print("Parallel: 4")
    print("Auto-switches when stagnant!")
    print("")

    config = PipelineConfig(
        experiment_name="adaptive_search",
        dataset_path=dataset_path,
        initial_strategy=SearchStrategy.GRID,  # Start conservador
        hyperparameter_space=HyperparameterSpace(),
        max_trials=50,
        max_parallel_trials=4,
        patience=10,  # Switch faster
        min_improvement=0.005  # Menos rigoroso
    )

    workflow_id = await start_adaptive_pipeline(config)

    print("")
    print("✅ Workflow started!")
    print(f"   Workflow ID: {workflow_id}")
    print(f"   Watch strategy evolution in Temporal UI!")
    print(f"   Temporal UI: http://localhost:8088/namespaces/default/workflows/{workflow_id}")
    print("")

    return workflow_id


async def run_custom(dataset_path: str = "imdb") -> str:
    """
    Example 3: Custom Multi-Phase Workflow

    Perfect for:
    - Expert users
    - Known good regions
    - Multi-stage refinement

    Flow:
    - Phase 1: Quick random exploration (10 trials)
    - Phase 2: Extract best region
    - Phase 3: Focused Bayesian search in that region (30 trials)

    This is more advanced - requires manual phase management
    For now, we'll run a focused Bayesian search
    """

    print("="*80)
    print("  🎨 Mode 3: Custom Multi-Phase")
    print("="*80)
    print("")
    print("Phase 1: Quick exploration (RANDOM)")
    print("Phase 2: Focused exploitation (BAYESIAN)")
    print("")

    # Phase 1: Quick exploration
    phase1_config = PipelineConfig(
        experiment_name="custom_phase1_exploration",
        dataset_path=dataset_path,
        initial_strategy=SearchStrategy.RANDOM,
        hyperparameter_space=HyperparameterSpace(),
        max_trials=10,
        max_parallel_trials=4
    )

    print("🔍 Phase 1: Starting exploration...")
    workflow_id_p1 = await start_adaptive_pipeline(phase1_config)
    print(f"   Workflow ID: {workflow_id_p1}")

    # TODO: Wait for phase 1 to complete, extract best region, start phase 2
    # For now, we just start a second workflow
    # Full implementation would query Temporal workflow result

    # Phase 2: Focused search (narrower space around best from phase 1)
    # For demo, we use a narrower learning rate range
    narrow_space = HyperparameterSpace(
        learning_rate=(1e-5, 5e-4),  # Narrower than default
        batch_size=[32, 64],  # Fewer options
        num_epochs=(5, 10),
        weight_decay=(0.0, 0.05),
        warmup_steps=(0, 500)
    )

    phase2_config = PipelineConfig(
        experiment_name="custom_phase2_focused",
        dataset_path=dataset_path,
        initial_strategy=SearchStrategy.BAYESIAN,
        hyperparameter_space=narrow_space,
        max_trials=30,
        max_parallel_trials=4
    )

    print("")
    print("🎯 Phase 2: Starting focused search...")
    workflow_id_p2 = await start_adaptive_pipeline(phase2_config)
    print(f"   Workflow ID: {workflow_id_p2}")

    print("")
    print("✅ Multi-phase workflow started!")
    print(f"   Phase 1: {workflow_id_p1}")
    print(f"   Phase 2: {workflow_id_p2}")
    print("")

    return workflow_id_p2


async def run_from_config(config_path: str) -> str:
    """
    Run from custom config file

    Example config.json:
    {
        "experiment_name": "my_experiment",
        "dataset_path": "imdb",
        "initial_strategy": "random",
        "max_trials": 100,
        "max_parallel_trials": 8,
        "hyperparameter_space": {
            "learning_rate": [1e-5, 1e-3],
            "batch_size": [16, 32, 64, 128],
            "num_epochs": [3, 10],
            "weight_decay": [0.0, 0.1],
            "warmup_steps": [0, 1000]
        }
    }
    """

    print("="*80)
    print(f"  📄 Running from config: {config_path}")
    print("="*80)
    print("")

    # Load config
    config_dict = json.loads(Path(config_path).read_text())

    # Create PipelineConfig
    config = PipelineConfig(**config_dict)

    print(f"Experiment: {config.experiment_name}")
    print(f"Strategy: {config.initial_strategy}")
    print(f"Trials: {config.max_trials}")
    print("")

    workflow_id = await start_adaptive_pipeline(config)

    print("")
    print("✅ Workflow started!")
    print(f"   Workflow ID: {workflow_id}")
    print("")

    return workflow_id


# ============================================================================
# CLI Interface
# ============================================================================

async def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        description="Neutron ML Pipeline - Adaptive Hyperparameter Optimization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py 1                     # Basic random search (20 trials)
  python main.py 2                     # Adaptive multi-strategy (50 trials)
  python main.py 3                     # Custom multi-phase workflow
  python main.py --config config.json  # Run from config file

  python main.py 1 --dataset glue      # Use different dataset

Quick Start:
  1. Start infrastructure:  just infra-up
  2. Start worker:          just worker-bg
  3. Run pipeline:          python main.py 1
  4. Monitor:               just ui

Full Documentation:
  See README.md for detailed examples and architecture
        """
    )

    parser.add_argument(
        "mode",
        type=str,
        nargs="?",
        choices=["1", "2", "3"],
        help="Pipeline mode: 1=basic, 2=adaptive, 3=custom"
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        help="Path to config JSON file"
    )

    parser.add_argument(
        "--dataset", "-d",
        type=str,
        default="imdb",
        help="Dataset path or HuggingFace dataset name (default: imdb)"
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.mode and not args.config:
        parser.print_help()
        sys.exit(1)

    # Print banner
    print("")
    print("╔"+"═"*78+"╗")
    print("║" + "  🚀 Neutron ML Pipeline - Temporal + Ray + MLflow".center(78) + "║")
    print("║" + "  Adaptive Hyperparameter Optimization".center(78) + "║")
    print("╚"+"═"*78+"╝")
    print("")

    # Route to appropriate pipeline
    try:
        if args.config:
            workflow_id = await run_from_config(args.config)
        elif args.mode == "1":
            workflow_id = await run_basic(args.dataset)
        elif args.mode == "2":
            workflow_id = await run_adaptive(args.dataset)
        elif args.mode == "3":
            workflow_id = await run_custom(args.dataset)
        else:
            parser.print_help()
            sys.exit(1)

        print("─"*80)
        print("Next Steps:")
        print("  • Monitor in Temporal UI:  http://localhost:8088")
        print("  • View metrics in MLflow:  http://localhost:5000")
        print("  • Check worker logs:       tail -f worker.log")
        print("  • Get workflow status:     just workflow-status " + workflow_id)
        print("─"*80)
        print("")

    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ required")
        sys.exit(1)

    # Run async main
    asyncio.run(main())
