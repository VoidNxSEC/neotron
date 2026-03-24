"""
Phase 2 Demo: Cerebro Semantic Optimizer
----------------------------------------
Demonstrates the integration of PHANTOM Cerebro Optimizer
with LLM reasoning and MLflow tracking.
"""

import logging
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("demo_phase2")

try:
    import mlflow
except ImportError:
    logger.warning("MLflow not installed. Skipping MLflow tracking.")
    mlflow = None

from neutron.core.models import (
    HyperparameterSpace,
    OptimizationState,
    SearchStrategy,
)
from neutron.plugins.cerebro_optimizer import CerebroOptimizer


def main():
    print("🚀 Neutron Phase 2: PHANTOM Cerebro Integration")
    print("===============================================")
    
    # 1. Define Search Space
    print("\n1. Defining Hyperparameter Space...")
    space = HyperparameterSpace(
        learning_rate=(1e-5, 5e-5),
        batch_size=[16, 32, 64],
        num_epochs=[3, 4, 5],
        warmup_steps=[0, 100, 500]
    )
    print(f"   Space: {space}")

    # 2. Initialize Optimizer
    print("\n2. Initializing Cerebro Optimizer...")
    try:
        optimizer = CerebroOptimizer(space, config_path="config/integrations.yaml")
        print(f"   Initialized with model: {optimizer.model}")
    except Exception as e:
        print(f"   Failed to initialize optimizer: {e}")
        return

    # 3. Simulate Optimization Loop
    print("\n3. Starting Semantic Optimization Loop...")
    
    experiment_name = "Cerebro_Phase2_Demo"
    if mlflow:
        mlflow.set_experiment(experiment_name)
        
    # Mock state
    state = OptimizationState(
        current_strategy=SearchStrategy.SEMANTIC,
        trials_completed=0,
        best_accuracy=0.0
    )
    
    with mlflow.start_run(run_name="semantic-search-demo") if mlflow else (lambda: None)():
        if mlflow:
            mlflow.log_param("strategy", "semantic")
            print("   MLflow run started.")

        print("\n   🤖 Querying LLM for suggestions...")
        start_time = time.time()
        
        # Request suggestions
        configs = optimizer.suggest_configs(
            num=3, 
            state=state, 
            experiment_id=experiment_name
        )
        
        duration = time.time() - start_time
        print(f"   Received {len(configs)} suggestions in {duration:.2f}s")
        
        for i, config in enumerate(configs):
            print(f"\n   [Suggestion {i+1}]")
            print(f"     LR: {config.learning_rate}")
            print(f"     BS: {config.batch_size}")
            print(f"     Epochs: {config.num_epochs}")
            print(f"     Weight Decay: {config.weight_decay}")
            
            # Log metrics to MLflow just to show we can
            if mlflow:
                with mlflow.start_run(run_name=f"trial-{i+1}", nested=True):
                    mlflow.log_params({
                        "learning_rate": config.learning_rate,
                        "batch_size": config.batch_size,
                        "num_epochs": config.num_epochs
                    })

    print("\n✅ Phase 2 Demo Complete!")
    print("   Check MLflow UI for detailed reasoning and prompts.")


if __name__ == "__main__":
    main()
