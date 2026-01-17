"""
Model training with Ray actors
"""

from neutron.training.trainers import TrainerPool, create_trainer_pool

__all__ = ["TrainerPool", "create_trainer_pool"]
