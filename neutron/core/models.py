"""
Core data models - Type-safe, composable primitives
Filosofia: Se o compilador/runtime não pode validar, você tá fazendo errado
"""
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional, Dict, Any, List, Union, Tuple
from datetime import datetime
from enum import Enum
import random
import itertools
import math


class SearchStrategy(str, Enum):
    """Estratégias de busca - cada uma com suas próprias características"""
    GRID = "grid"              # Exhaustivo, previsível
    RANDOM = "random"          # Exploratório, rápido
    BAYESIAN = "bayesian"      # Adaptativo, eficiente
    EVOLUTIONARY = "evolutionary"  # Criativo, pode descobrir regiões inesperadas


class HyperparameterSpace(BaseModel):
    """Define o espaço de busca - composable e validável"""
    learning_rate: tuple[float, float] = (1e-5, 1e-3)
    batch_size: List[int] = [16, 32, 64, 128]
    num_epochs: tuple[int, int] = (5, 20)
    weight_decay: tuple[float, float] = (0.0, 0.1)
    warmup_steps: tuple[int, int] = (0, 1000)
    
    @validator('learning_rate', 'num_epochs', 'weight_decay', 'warmup_steps')
    def validate_ranges(cls, v):
        if v[0] >= v[1]:
            raise ValueError(f"Invalid range: {v}")
        return v

    def sample_random(self) -> Dict[str, Any]:
        """Sample random hyperparameters from the search space"""
        result = {}

        # Learning rate
        if isinstance(self.learning_rate, tuple):
            # Continuous range - sample log-uniform
            min_lr, max_lr = self.learning_rate
            log_min = random.uniform(float(min_lr), float(max_lr))
            result["learning_rate"] = log_min
        else:
            # Discrete list
            result["learning_rate"] = random.choice(self.learning_rate)

        # Weight decay
        if isinstance(self.weight_decay, tuple):
            min_wd, max_wd = self.weight_decay
            result["weight_decay"] = random.uniform(float(min_wd), float(max_wd))
        else:
            result["weight_decay"] = random.choice(self.weight_decay)

        # Warmup steps
        if isinstance(self.warmup_steps, tuple):
            min_ws, max_ws = self.warmup_steps
            result["warmup_steps"] = random.randint(int(min_ws), int(max_ws))
        else:
            result["warmup_steps"] = random.choice(self.warmup_steps)

        # Num epochs
        if isinstance(self.num_epochs, tuple):
            min_ep, max_ep = self.num_epochs
            result["num_epochs"] = random.randint(int(min_ep), int(max_ep))
        else:
            result["num_epochs"] = random.choice(self.num_epochs)

        # Batch size
        if isinstance(self.batch_size, tuple):
            min_bs, max_bs = self.batch_size
            result["batch_size"] = random.randint(int(min_bs), int(max_bs))
        else:
            result["batch_size"] = random.choice(self.batch_size)

        return result

    def get_grid_points(self, points_per_dim: int = 3) -> List[Dict[str, Any]]:
        """
        Generate grid points for grid search.

        Args:
            points_per_dim: Number of points to sample per dimension for continuous ranges

        Returns:
            List of hyperparameter dictionaries representing grid points
        """
        # Generate values for each dimension
        lr_values = self._get_dimension_values(self.learning_rate, points_per_dim, log_scale=True)
        wd_values = self._get_dimension_values(self.weight_decay, points_per_dim, log_scale=False)
        ws_values = self._get_dimension_values(self.warmup_steps, points_per_dim, log_scale=False, as_int=True)
        ep_values = self._get_dimension_values(self.num_epochs, points_per_dim, log_scale=False, as_int=True)
        bs_values = self._get_dimension_values(self.batch_size, points_per_dim, log_scale=False, as_int=True)

        # Generate all combinations
        grid_points = []
        for lr, wd, ws, ep, bs in itertools.product(lr_values, wd_values, ws_values, ep_values, bs_values):
            grid_points.append({
                "learning_rate": lr,
                "weight_decay": wd,
                "warmup_steps": ws,
                "num_epochs": ep,
                "batch_size": bs
            })

        return grid_points

    def _get_dimension_values(
        self,
        dimension: Union[Tuple, List],
        points_per_dim: int,
        log_scale: bool = False,
        as_int: bool = False
    ) -> List:
        """Helper to get values for a single dimension"""
        if isinstance(dimension, list):
            # Already discrete
            return dimension

        # Continuous range
        min_val, max_val = dimension

        if log_scale:
            # Log-scale sampling for learning rate
            log_min = math.log10(min_val)
            log_max = math.log10(max_val)
            values = [10 ** (log_min + i * (log_max - log_min) / (points_per_dim - 1))
                     for i in range(points_per_dim)]
        else:
            # Linear scale
            step = (max_val - min_val) / (points_per_dim - 1)
            values = [min_val + i * step for i in range(points_per_dim)]

        if as_int:
            values = [int(round(v)) for v in values]

        return values


class TrainingConfig(BaseModel):
    """Config completa pra um training run"""
    model_name: str = "distilbert-base-uncased"
    dataset_path: str
    output_dir: str = "/tmp/model_outputs"
    
    # Hyperparameters (podem vir do optimizer)
    learning_rate: float
    batch_size: int
    num_epochs: int
    weight_decay: float = 0.01
    warmup_steps: int = 100
    
    # Infrastructure
    use_gpu: bool = True
    mixed_precision: bool = True
    gradient_accumulation_steps: int = 1
    
    # Metadata
    experiment_id: str
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.now)


class MetricResult(BaseModel):
    """Resultado de uma métrica - primeiro-class citizen, não dicts soltos"""
    name: str
    value: float
    step: int
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = {}


class TrainingResult(BaseModel):
    """Resultado completo de um training run"""
    run_id: str
    config: TrainingConfig
    metrics: List[MetricResult]
    
    # Summary metrics
    best_accuracy: float
    best_loss: float
    training_time_seconds: float
    
    # Artifacts
    model_path: Optional[str] = None
    checkpoint_paths: List[str] = []
    
    # Status
    status: Literal["success", "failed", "timeout"] = "success"
    error_message: Optional[str] = None
    
    @property
    def score(self) -> float:
        """Unified score pra comparação - você pode customizar"""
        # Exemplo: balanceia accuracy e tempo
        time_penalty = min(self.training_time_seconds / 3600, 1.0)  # Normaliza por hora
        return self.best_accuracy * (1 - 0.2 * time_penalty)


class OptimizationState(BaseModel):
    """Estado da otimização - permite adaptive strategy"""
    strategy: SearchStrategy
    hyperparameter_space: HyperparameterSpace
    
    # Histórico de trials
    completed_trials: List[TrainingResult] = []
    failed_trials: int = 0
    
    # Adaptive parameters
    exploration_rate: float = 0.5  # Alta no início, decresce com time
    best_score_so_far: float = 0.0
    trials_since_improvement: int = 0
    
    # Resource allocation
    max_parallel_trials: int = 4
    timeout_seconds: int = 7200  # 2 hours per trial
    
    def should_switch_strategy(self) -> bool:
        """Adaptive logic - troca de estratégia se tá estagnado"""
        return (
            self.trials_since_improvement > 10 and 
            self.strategy != SearchStrategy.EVOLUTIONARY
        )
    
    def get_next_strategy(self) -> SearchStrategy:
        """Strategy evolution - começa conservador, fica agressivo"""
        if self.strategy == SearchStrategy.GRID:
            return SearchStrategy.RANDOM
        elif self.strategy == SearchStrategy.RANDOM:
            return SearchStrategy.BAYESIAN
        else:
            return SearchStrategy.EVOLUTIONARY


class PipelineConfig(BaseModel):
    """Config master do pipeline completo"""
    experiment_name: str
    dataset_path: str
    
    # Optimization
    initial_strategy: SearchStrategy = SearchStrategy.RANDOM
    hyperparameter_space: HyperparameterSpace = Field(default_factory=HyperparameterSpace)
    max_trials: int = 50
    max_parallel_trials: int = 4
    
    # Infrastructure
    ray_address: Optional[str] = None  # None = local mode
    mlflow_tracking_uri: str = "http://localhost:5000"
    
    # Early stopping
    patience: int = 15  # trials sem melhoria
    min_improvement: float = 0.01  # melhoria mínima considerável
    
    class Config:
        use_enum_values = True
