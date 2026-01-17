"""
Tests for cost tracking
"""
import pytest
from neutron.tracking.cost_tracker import CostConfig


def test_cost_config_initialization():
    """Test cost configuration"""
    config = CostConfig(
        gpu_hour_cost=1.5,
        cpu_hour_cost=0.1,
        storage_gb_month_cost=0.02
    )
    assert config.gpu_hour_cost == 1.5
    assert config.cpu_hour_cost == 0.1


def test_cost_tracker_initialization(mlflow_uri):
    """Test CostTracker initialization"""
    from neutron.tracking.cost_tracker import CostTracker

    tracker = CostTracker(mlflow_uri=mlflow_uri)
    assert tracker.mlflow_uri == mlflow_uri


# Mark as integration test - requires MLflow
@pytest.mark.skip(reason="Requires MLflow server - run as integration tests")
def test_analyze_experiment_costs():
    """Test analyzing experiment costs"""
    # TODO: Implement integration test with MLflow
    pass
