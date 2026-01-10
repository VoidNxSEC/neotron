"""
Temporal Workflow - O cérebro orchestrator
Filosofia: Workflows são código, não YAML. Durable execution significa que crashes são NBD.
"""
from temporalio import workflow, activity
from temporalio.common import RetryPolicy
from datetime import timedelta
from typing import List, Optional
import asyncio

from models import (
    PipelineConfig, TrainingConfig, TrainingResult,
    OptimizationState, SearchStrategy, HyperparameterSpace
)
from optimizer import HyperparameterOptimizer


# ============================================================================
# Activities - Unidades atômicas de trabalho
# Activities são retryable, timeout-able, observable
# ============================================================================

@activity.defn(name="train_model_batch")
async def train_model_batch_activity(
    configs: List[TrainingConfig],
    pool_ref: str  # Ray ObjectRef serializado
) -> List[TrainingResult]:
    """
    Activity que dispara batch de training no Ray cluster
    Se falhar, Temporal vai retry automaticamente
    """
    import ray
    
    # Reconstruct pool reference
    pool = ray.get_actor(pool_ref)
    
    # Dispatch to pool
    results_ref = pool.train_batch.remote(configs)
    results = await results_ref
    
    return results


@activity.defn(name="setup_mlflow")
async def setup_mlflow_activity(experiment_name: str, tracking_uri: str) -> str:
    """Setup MLflow experiment e retorna experiment_id"""
    import mlflow
    
    mlflow.set_tracking_uri(tracking_uri)
    
    # Create or get experiment
    try:
        experiment_id = mlflow.create_experiment(experiment_name)
    except Exception:
        experiment = mlflow.get_experiment_by_name(experiment_name)
        experiment_id = experiment.experiment_id
    
    mlflow.set_experiment(experiment_name)
    
    return experiment_id


@activity.defn(name="validate_gcp_credits")
async def validate_gcp_credits_activity(
    estimated_cost: float,
    gcp_project_id: str = "gen-lang-client-0530325234"
) -> dict:
    """
    Pre-flight GCP credit validation usando CEREBRO

    Args:
        estimated_cost: Estimated cost of upcoming training (USD)
        gcp_project_id: GCP project ID

    Returns:
        Dict with approval status and credit info
    """
    from cost_tracker import CerebroCreditValidator

    validator = CerebroCreditValidator(project_id=gcp_project_id)
    validation_result = validator.validate_credits_before_run(estimated_cost)

    # Log result
    if validation_result["approved"]:
        print(f"✅ Credit validation passed")
        print(f"   Credits remaining: ${validation_result.get('credits_remaining', 0):.2f}")
        print(f"   Burn rate: ${validation_result.get('burn_rate_per_day', 0):.2f}/day")
    else:
        print(f"❌ Credit validation failed: {validation_result['reason']}")
        print(f"   Recommendation: {validation_result.get('recommendation', 'N/A')}")

    return validation_result


@activity.defn(name="analyze_results")
async def analyze_results_activity(
    results: List[TrainingResult],
    state: OptimizationState
) -> dict:
    """
    Analisa batch de resultados e retorna insights
    Pode ser expandido com feature importance, correlation analysis, etc
    """
    successful = [r for r in results if r.status == "success"]
    
    if not successful:
        return {
            "all_failed": True,
            "analysis": None
        }
    
    # Extract metrics
    scores = [r.score for r in successful]
    accuracies = [r.best_accuracy for r in successful]
    times = [r.training_time_seconds for r in successful]
    
    analysis = {
        "all_failed": False,
        "num_successful": len(successful),
        "num_failed": len(results) - len(successful),
        "best_score": max(scores),
        "mean_score": sum(scores) / len(scores),
        "best_accuracy": max(accuracies),
        "mean_accuracy": sum(accuracies) / len(accuracies),
        "total_training_time": sum(times),
        "avg_training_time": sum(times) / len(times),
    }
    
    return analysis


# ============================================================================
# Workflow - A orchestration logic
# Workflows são determinísticas, versionáveis, e completamente observáveis
# ============================================================================

@workflow.defn(name="AdaptiveMLPipeline")
class AdaptiveMLPipelineWorkflow:
    """
    Workflow principal - coordena todo o pipeline
    
    Key features:
    - Durable execution (sobrevive worker crashes)
    - Dynamic DAG (muda estratégia mid-flight)
    - Full observability (cada step rastreável)
    - Composable (você pode chamar sub-workflows)
    """
    
    @workflow.run
    async def run(self, config: PipelineConfig) -> dict:
        """
        Main workflow loop
        Cada iteração é um batch de trials, e o workflow adapta estratégia
        """
        
        # 1. Setup - executa uma vez, durável
        workflow.logger.info(f"Starting pipeline: {config.experiment_name}")
        
        experiment_id = await workflow.execute_activity(
            setup_mlflow_activity,
            args=[config.experiment_name, config.mlflow_tracking_uri],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3)
        )
        
        # 2. Initialize optimization state
        opt_state = OptimizationState(
            strategy=config.initial_strategy,
            hyperparameter_space=config.hyperparameter_space,
            max_parallel_trials=config.max_parallel_trials,
        )
        
        optimizer = HyperparameterOptimizer(opt_state)
        
        # 3. Main optimization loop - DYNAMIC
        iteration = 0
        trials_completed = 0
        
        while trials_completed < config.max_trials:
            iteration += 1
            workflow.logger.info(
                f"Iteration {iteration} - Strategy: {opt_state.strategy}, "
                f"Trials: {trials_completed}/{config.max_trials}"
            )
            
            # 3.1 Generate next batch of configs
            # O optimizer decide quantos e quais configs baseado na estratégia
            num_parallel = min(
                opt_state.max_parallel_trials,
                config.max_trials - trials_completed
            )
            
            configs = optimizer.suggest_configs(num_parallel, experiment_id)
            
            # 3.2 Train batch in parallel
            # Ray distribui entre workers, Temporal monitora progresso
            results = await workflow.execute_activity(
                train_model_batch_activity,
                args=[configs, f"trainer_pool_{experiment_id}"],
                start_to_close_timeout=timedelta(seconds=opt_state.timeout_seconds),
                retry_policy=RetryPolicy(
                    maximum_attempts=2,
                    initial_interval=timedelta(seconds=10),
                )
            )
            
            trials_completed += len(results)
            
            # 3.3 Analyze results
            analysis = await workflow.execute_activity(
                analyze_results_activity,
                args=[results, opt_state],
                start_to_close_timeout=timedelta(seconds=30),
            )
            
            workflow.logger.info(f"Batch analysis: {analysis}")
            
            # 3.4 Update optimizer state - ADAPTIVE LOGIC
            optimizer.update_state(results)
            
            # 3.5 Early stopping check
            if await self._should_early_stop(opt_state, config):
                workflow.logger.info("Early stopping triggered")
                break
            
            # 3.6 Sleep entre iterations (backpressure control)
            await asyncio.sleep(5)
        
        # 4. Final summary
        best_trial = max(
            opt_state.completed_trials,
            key=lambda x: x.score
        ) if opt_state.completed_trials else None
        
        summary = {
            "experiment_id": experiment_id,
            "total_trials": len(opt_state.completed_trials),
            "failed_trials": opt_state.failed_trials,
            "final_strategy": opt_state.strategy.value,
            "best_score": opt_state.best_score_so_far,
            "best_trial": best_trial.model_dump() if best_trial else None,
        }
        
        workflow.logger.info(f"Pipeline completed: {summary}")
        return summary
    
    async def _should_early_stop(
        self,
        state: OptimizationState,
        config: PipelineConfig
    ) -> bool:
        """
        Early stopping logic - para se não tá melhorando
        Você pode customizar isso com critérios mais sofisticados
        """
        if state.trials_since_improvement >= config.patience:
            # Check se a melhoria foi significativa
            if len(state.completed_trials) < 10:
                return False  # Deixa warm up
            
            recent_trials = state.completed_trials[-config.patience:]
            score_variance = np.var([t.score for t in recent_trials])
            
            return score_variance < config.min_improvement
        
        return False


# ============================================================================
# Sub-Workflows - Composable orchestration
# Você pode ter workflows que chamam outros workflows
# ============================================================================

@workflow.defn(name="EnsembleTrainingWorkflow")
class EnsembleTrainingWorkflow:
    """
    Exemplo de sub-workflow - treina ensemble de models
    Pode ser chamado pelo workflow principal ou standalone
    """
    
    @workflow.run
    async def run(
        self,
        base_config: TrainingConfig,
        num_models: int = 5
    ) -> List[TrainingResult]:
        """Train ensemble com diferentes seeds"""
        
        # Generate configs com seeds diferentes
        configs = []
        for i in range(num_models):
            config = base_config.model_copy(deep=True)
            config.run_id = f"{base_config.run_id}_ensemble_{i}"
            configs.append(config)
        
        # Train all in parallel
        results = await workflow.execute_activity(
            train_model_batch_activity,
            args=[configs, "trainer_pool"],
            start_to_close_timeout=timedelta(hours=2),
        )
        
        return results


# ============================================================================
# Workflow Queries - Runtime introspection
# Permite inspecionar estado do workflow enquanto ele roda
# ============================================================================

@workflow.defn(name="AdaptiveMLPipelineWithQueries")
class AdaptiveMLPipelineWithQueries(AdaptiveMLPipelineWorkflow):
    """
    Extended workflow com queries - permite monitoramento real-time
    """
    
    def __init__(self):
        super().__init__()
        self.current_iteration = 0
        self.current_strategy = None
        self.latest_results = []
    
    @workflow.query
    def get_progress(self) -> dict:
        """Query atual estado - callable durante execução"""
        return {
            "iteration": self.current_iteration,
            "strategy": self.current_strategy,
            "num_results": len(self.latest_results),
        }
    
    @workflow.signal
    async def update_config(self, new_max_trials: int):
        """Signal pra alterar config mid-flight"""
        workflow.logger.info(f"Updating max_trials to {new_max_trials}")
        # Update config dynamically
        pass


# Helper pra facilitar o uso
async def start_adaptive_pipeline(
    config: PipelineConfig,
    workflow_id: Optional[str] = None
) -> str:
    """
    Helper function pra iniciar workflow
    Retorna workflow_id pra tracking
    """
    from temporalio.client import Client
    
    client = await Client.connect("localhost:7233")
    
    workflow_id = workflow_id or f"ml-pipeline-{config.experiment_name}"
    
    handle = await client.start_workflow(
        AdaptiveMLPipelineWorkflow.run,
        args=[config],
        id=workflow_id,
        task_queue="ml-pipeline-queue",
    )
    
    workflow.logger.info(f"Started workflow: {workflow_id}")
    return workflow_id
