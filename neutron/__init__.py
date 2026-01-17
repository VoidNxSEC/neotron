"""
Neutron ML Pipeline - Adaptive Hyperparameter Optimization

A production-grade ML orchestration framework with:
- Temporal workflows for durable execution
- Ray for distributed training
- MLflow for experiment tracking
- Adaptive search strategies (Grid, Random, Bayesian, Evolutionary)
"""

__version__ = "0.1.0"

# Core exports
from neutron.core.models import (
    PipelineConfig,
    TrainingConfig,
    TrainingResult,
    HyperparameterSpace,
    SearchStrategy,
    OptimizationState,
    MetricResult
)

from neutron.optimization.optimizer import HyperparameterOptimizer
from neutron.training.trainers import TrainerPool, create_trainer_pool
from neutron.orchestration.workflows import start_adaptive_pipeline
from neutron.tracking.cost_tracker import CostTracker, CerebroCreditValidator
from neutron.integration.unified_cost_reporter import UnifiedCostReporter

__all__ = [
    # Version
    "__version__",

    # Core Models
    "PipelineConfig",
    "TrainingConfig",
    "TrainingResult",
    "HyperparameterSpace",
    "SearchStrategy",
    "OptimizationState",
    "MetricResult",

    # Optimization
    "HyperparameterOptimizer",

    # Training
    "TrainerPool",
    "create_trainer_pool",

    # Orchestration
    "start_adaptive_pipeline",

    # Tracking
    "CostTracker",
    "CerebroCreditValidator",

    # Integration
    "UnifiedCostReporter",
]
