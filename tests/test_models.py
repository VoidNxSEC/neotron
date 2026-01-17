"""
Tests for core data models
"""

from neutron.core.models import (
    HyperparameterSpace,
    OptimizationState,
    SearchStrategy,
    TrainingConfig,
)


def test_hyperparameter_space_creation():
    """Test creating a hyperparameter space"""
    space = HyperparameterSpace(
        learning_rate=(1e-5, 1e-3), batch_size=[8, 16, 32], num_epochs=[1, 2, 3]
    )
    assert space.learning_rate == (1e-5, 1e-3)
    assert space.batch_size == [8, 16, 32]


def test_hyperparameter_space_sampling(sample_hyperparameter_space):
    """Test sampling from hyperparameter space"""
    sample = sample_hyperparameter_space.sample()
    assert isinstance(sample, dict)
    assert "learning_rate" in sample
    assert "batch_size" in sample
    assert sample["batch_size"] in [8, 16, 32]


def test_pipeline_config_creation(sample_pipeline_config):
    """Test creating a pipeline configuration"""
    assert sample_pipeline_config.experiment_id == "test-experiment"
    assert sample_pipeline_config.search_strategy == SearchStrategy.RANDOM
    assert sample_pipeline_config.max_trials == 5


def test_training_config_creation():
    """Test creating a training configuration"""
    config = TrainingConfig(
        run_id="test-run-1",
        experiment_id="test-experiment",
        model_name="distilbert-base-uncased",
        dataset_path="imdb",
        learning_rate=1e-4,
        batch_size=16,
        num_epochs=2,
    )
    assert config.run_id == "test-run-1"
    assert config.learning_rate == 1e-4


def test_optimization_state_initialization():
    """Test optimization state tracking"""
    state = OptimizationState(
        current_strategy=SearchStrategy.RANDOM, trials_completed=0, best_accuracy=0.0
    )
    assert state.current_strategy == SearchStrategy.RANDOM
    assert state.trials_completed == 0
