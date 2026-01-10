"""
Hyperparameter Optimizer - The Brain of Adaptive Search
Filosofia: Smart exploration → Intelligent exploitation → Creative discovery

Strategies:
- GRID: Systematic, exhaustive (use when space is small and discrete)
- RANDOM: Fast exploration, good baseline (always a solid choice)
- BAYESIAN: Sample-efficient, models uncertainty (best for expensive evals)
- EVOLUTIONARY: Creative, discovers unexpected regions (when stuck in local optima)
"""
import random
import itertools
import numpy as np
from typing import List, Optional, Dict, Any, Protocol
from datetime import datetime
import uuid

from models import (
    OptimizationState, TrainingConfig, TrainingResult,
    SearchStrategy, HyperparameterSpace
)


# ============================================================================
# Plugin Protocol - Para extensões futuras (CEREBRO, etc)
# ============================================================================

class OptimizerPlugin(Protocol):
    """Protocol para plugins externos de otimização"""

    def suggest_configs(
        self,
        num: int,
        state: OptimizationState,
        experiment_id: str
    ) -> List[TrainingConfig]:
        """Suggest hyperparameter configs"""
        ...

    def update_from_results(self, results: List[TrainingResult]) -> None:
        """Update internal state from training results"""
        ...


# ============================================================================
# Main Optimizer Class
# ============================================================================

class HyperparameterOptimizer:
    """
    Adaptive hyperparameter optimizer com múltiplas estratégias

    Features:
    - 4 built-in strategies (GRID, RANDOM, BAYESIAN, EVOLUTIONARY)
    - Adaptive strategy switching baseado em performance
    - Plugin support pra algoritmos custom (CEREBRO semantic search, etc)
    - Stateful - mantém histórico pra Bayesian/Evolutionary
    """

    def __init__(
        self,
        state: OptimizationState,
        plugin: Optional[OptimizerPlugin] = None
    ):
        self.state = state
        self.plugin = plugin

        # Bayesian optimization state
        self.bayesian_samples = []  # (config, score) pairs
        self.bayesian_model = None

        # Evolutionary state
        self.population = []  # Current generation
        self.generation = 0

        # Grid search state
        self.grid_iterator = None
        self.grid_exhausted = False

    def suggest_configs(
        self,
        num: int,
        experiment_id: str
    ) -> List[TrainingConfig]:
        """
        Generate next batch of configs to try

        Args:
            num: Number of configs to generate
            experiment_id: MLflow experiment ID

        Returns:
            List of TrainingConfigs ready for training
        """

        # Se tem plugin, delega pra ele
        if self.plugin:
            return self.plugin.suggest_configs(num, self.state, experiment_id)

        # Dispatch pra estratégia correta
        if self.state.strategy == SearchStrategy.GRID:
            configs = self._grid_search(num)
        elif self.state.strategy == SearchStrategy.RANDOM:
            configs = self._random_search(num)
        elif self.state.strategy == SearchStrategy.BAYESIAN:
            configs = self._bayesian_search(num)
        elif self.state.strategy == SearchStrategy.EVOLUTIONARY:
            configs = self._evolutionary_search(num)
        else:
            raise ValueError(f"Unknown strategy: {self.state.strategy}")

        # Adiciona metadata comum
        for config in configs:
            config.experiment_id = experiment_id
            config.run_id = f"{experiment_id}_{uuid.uuid4().hex[:8]}"
            config.timestamp = datetime.now()

        return configs

    def update_state(self, results: List[TrainingResult]) -> None:
        """
        Update optimizer state baseado em resultados de training

        Args:
            results: List of TrainingResults from completed runs
        """

        # Update state with new results
        for result in results:
            if result.status == "success":
                self.state.completed_trials.append(result)

                # Check se melhorou
                if result.score > self.state.best_score_so_far:
                    improvement = result.score - self.state.best_score_so_far
                    self.state.best_score_so_far = result.score
                    self.state.trials_since_improvement = 0
                    print(f"🎯 New best score: {result.score:.4f} (+{improvement:.4f})")
                else:
                    self.state.trials_since_improvement += 1

                # Update strategy-specific state
                if self.state.strategy == SearchStrategy.BAYESIAN:
                    self.bayesian_samples.append((result.config, result.score))

                if self.state.strategy == SearchStrategy.EVOLUTIONARY:
                    self.population.append((result.config, result.score))
            else:
                self.state.failed_trials += 1

        # Check se deve trocar estratégia
        if self.state.should_switch_strategy():
            old_strategy = self.state.strategy
            self.state.strategy = self.state.get_next_strategy()
            print(f"🔄 Strategy switch: {old_strategy} → {self.state.strategy}")
            print(f"   Reason: {self.state.trials_since_improvement} trials without improvement")

        # Decay exploration rate over time
        total_trials = len(self.state.completed_trials)
        self.state.exploration_rate = max(0.1, 0.5 * (0.95 ** total_trials))

    # ========================================================================
    # Strategy Implementations
    # ========================================================================

    def _grid_search(self, num: int) -> List[TrainingConfig]:
        """
        Grid search - systematic exploration

        Pros: Exhaustive, reproducible, good for small discrete spaces
        Cons: Exponential growth, doesn't scale to continuous params
        """

        space = self.state.hyperparameter_space

        # Initialize grid iterator se necessário
        if self.grid_iterator is None:
            # Create grid
            learning_rates = np.linspace(
                space.learning_rate[0],
                space.learning_rate[1],
                num=5
            ).tolist()
            batch_sizes = space.batch_size
            num_epochs = list(range(space.num_epochs[0], space.num_epochs[1] + 1))
            weight_decays = np.linspace(
                space.weight_decay[0],
                space.weight_decay[1],
                num=3
            ).tolist()
            warmup_steps = [space.warmup_steps[0], space.warmup_steps[1]]

            # Cartesian product
            grid = itertools.product(
                learning_rates,
                batch_sizes,
                num_epochs,
                weight_decays,
                warmup_steps
            )
            self.grid_iterator = iter(grid)

        # Sample from grid
        configs = []
        for _ in range(num):
            try:
                lr, bs, epochs, wd, warmup = next(self.grid_iterator)
                config = TrainingConfig(
                    dataset_path="",  # Will be set by workflow
                    learning_rate=lr,
                    batch_size=int(bs),
                    num_epochs=int(epochs),
                    weight_decay=wd,
                    warmup_steps=int(warmup),
                    experiment_id="",  # Will be set later
                    run_id=""
                )
                configs.append(config)
            except StopIteration:
                self.grid_exhausted = True
                print("⚠️  Grid exhausted - switching to RANDOM")
                self.state.strategy = SearchStrategy.RANDOM
                # Fill remaining with random
                configs.extend(self._random_search(num - len(configs)))
                break

        return configs

    def _random_search(self, num: int) -> List[TrainingConfig]:
        """
        Random search - fast baseline, surprisingly effective

        Pros: Simple, parallelizable, no assumptions about space
        Cons: No learning from previous trials, can be wasteful

        Paper: "Random Search for Hyper-Parameter Optimization" (Bergstra & Bengio, 2012)
        """

        space = self.state.hyperparameter_space
        configs = []

        for _ in range(num):
            # Sample uniformly (log-uniform for learning rate)
            lr = 10 ** random.uniform(
                np.log10(space.learning_rate[0]),
                np.log10(space.learning_rate[1])
            )
            bs = random.choice(space.batch_size)
            epochs = random.randint(space.num_epochs[0], space.num_epochs[1])
            wd = random.uniform(space.weight_decay[0], space.weight_decay[1])
            warmup = random.randint(space.warmup_steps[0], space.warmup_steps[1])

            config = TrainingConfig(
                dataset_path="",
                learning_rate=lr,
                batch_size=bs,
                num_epochs=epochs,
                weight_decay=wd,
                warmup_steps=warmup,
                experiment_id="",
                run_id=""
            )
            configs.append(config)

        return configs

    def _bayesian_search(self, num: int) -> List[TrainingConfig]:
        """
        Bayesian optimization - sample-efficient exploration

        Pros: Models uncertainty, trades off exploration/exploitation
        Cons: Requires history, overhead of fitting surrogate model

        Strategy: Use Gaussian Process + Expected Improvement acquisition
        Fallback: Random search se não tem dados suficientes
        """

        # Need at least 5 samples pra fit GP
        if len(self.bayesian_samples) < 5:
            print("ℹ️  Bayesian: Not enough samples, using random")
            return self._random_search(num)

        space = self.state.hyperparameter_space
        configs = []

        # Extract X, y from samples
        X = []
        y = []
        for config, score in self.bayesian_samples:
            # Normalize features to [0, 1]
            x = [
                (np.log10(config.learning_rate) - np.log10(space.learning_rate[0])) /
                (np.log10(space.learning_rate[1]) - np.log10(space.learning_rate[0])),
                space.batch_size.index(config.batch_size) / len(space.batch_size),
                (config.num_epochs - space.num_epochs[0]) / (space.num_epochs[1] - space.num_epochs[0]),
                (config.weight_decay - space.weight_decay[0]) / (space.weight_decay[1] - space.weight_decay[0]),
                (config.warmup_steps - space.warmup_steps[0]) / (space.warmup_steps[1] - space.warmup_steps[0])
            ]
            X.append(x)
            y.append(score)

        X = np.array(X)
        y = np.array(y)

        # Fit simple Gaussian Process (sem sklearn dependency por enquanto)
        # Simplified: Sample from region near best performers
        # TODO: Proper GP with sklearn.gaussian_process.GaussianProcessRegressor

        # Get top 3 performers
        top_indices = np.argsort(y)[-3:]
        top_X = X[top_indices]

        for _ in range(num):
            # Sample near top performers with exploration noise
            base_idx = random.choice(range(len(top_X)))
            base_x = top_X[base_idx]

            # Add Gaussian noise (exploration vs exploitation)
            noise_scale = self.state.exploration_rate
            x_new = base_x + np.random.normal(0, noise_scale, size=base_x.shape)
            x_new = np.clip(x_new, 0, 1)  # Keep in bounds

            # Denormalize back to hyperparameters
            lr = 10 ** (x_new[0] * (np.log10(space.learning_rate[1]) - np.log10(space.learning_rate[0])) +
                       np.log10(space.learning_rate[0]))
            bs_idx = int(x_new[1] * len(space.batch_size))
            bs_idx = min(bs_idx, len(space.batch_size) - 1)
            bs = space.batch_size[bs_idx]
            epochs = int(x_new[2] * (space.num_epochs[1] - space.num_epochs[0]) + space.num_epochs[0])
            wd = x_new[3] * (space.weight_decay[1] - space.weight_decay[0]) + space.weight_decay[0]
            warmup = int(x_new[4] * (space.warmup_steps[1] - space.warmup_steps[0]) + space.warmup_steps[0])

            config = TrainingConfig(
                dataset_path="",
                learning_rate=lr,
                batch_size=bs,
                num_epochs=epochs,
                weight_decay=wd,
                warmup_steps=warmup,
                experiment_id="",
                run_id=""
            )
            configs.append(config)

        return configs

    def _evolutionary_search(self, num: int) -> List[TrainingConfig]:
        """
        Evolutionary optimization - creative discovery

        Pros: Can escape local optima, discovers unexpected good regions
        Cons: Needs population, can be slow to converge

        Strategy: Tournament selection + Gaussian mutation + Crossover
        """

        space = self.state.hyperparameter_space

        # Initialize population se necessário
        if len(self.population) < 10:
            print("ℹ️  Evolutionary: Initializing population")
            return self._random_search(num)

        # Sort population by fitness
        self.population.sort(key=lambda x: x[1], reverse=True)

        configs = []
        for _ in range(num):
            # Tournament selection (pick 3, choose best)
            tournament = random.sample(self.population[:20], 3)
            parent1 = max(tournament, key=lambda x: x[1])[0]

            tournament = random.sample(self.population[:20], 3)
            parent2 = max(tournament, key=lambda x: x[1])[0]

            # Crossover + Mutation
            if random.random() < 0.7:  # 70% crossover
                # Uniform crossover
                lr = random.choice([parent1.learning_rate, parent2.learning_rate])
                bs = random.choice([parent1.batch_size, parent2.batch_size])
                epochs = random.choice([parent1.num_epochs, parent2.num_epochs])
                wd = random.choice([parent1.weight_decay, parent2.weight_decay])
                warmup = random.choice([parent1.warmup_steps, parent2.warmup_steps])
            else:
                # Use parent1
                lr = parent1.learning_rate
                bs = parent1.batch_size
                epochs = parent1.num_epochs
                wd = parent1.weight_decay
                warmup = parent1.warmup_steps

            # Mutation (30% chance per gene)
            if random.random() < 0.3:
                lr *= random.uniform(0.5, 2.0)
                lr = np.clip(lr, space.learning_rate[0], space.learning_rate[1])

            if random.random() < 0.3:
                bs = random.choice(space.batch_size)

            if random.random() < 0.3:
                epochs = np.clip(
                    epochs + random.randint(-2, 2),
                    space.num_epochs[0],
                    space.num_epochs[1]
                )

            if random.random() < 0.3:
                wd += random.gauss(0, 0.02)
                wd = np.clip(wd, space.weight_decay[0], space.weight_decay[1])

            if random.random() < 0.3:
                warmup = np.clip(
                    warmup + random.randint(-100, 100),
                    space.warmup_steps[0],
                    space.warmup_steps[1]
                )

            config = TrainingConfig(
                dataset_path="",
                learning_rate=float(lr),
                batch_size=int(bs),
                num_epochs=int(epochs),
                weight_decay=float(wd),
                warmup_steps=int(warmup),
                experiment_id="",
                run_id=""
            )
            configs.append(config)

        self.generation += 1
        return configs


# ============================================================================
# Helper Functions
# ============================================================================

def load_optimizer_plugin(plugin_name: str) -> Optional[OptimizerPlugin]:
    """
    Dynamically load optimizer plugin

    Usage:
        plugin = load_optimizer_plugin("cerebro_semantic")
        optimizer = HyperparameterOptimizer(state, plugin=plugin)
    """

    if plugin_name == "cerebro_semantic":
        try:
            from plugins.cerebro_optimizer import CEREBROSemanticOptimizer
            return CEREBROSemanticOptimizer
        except ImportError:
            print(f"⚠️  Plugin '{plugin_name}' not found, using built-in strategies")
            return None

    print(f"⚠️  Unknown plugin: {plugin_name}")
    return None
