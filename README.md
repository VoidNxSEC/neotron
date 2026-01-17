# Adaptive ML Pipeline
**Temporal + Ray + MLflow = Máximo Controle, Zero Lock-in**

Pipeline de ML orchestration com estratégias adaptativas de hyperparameter search. Diferente do LangChain e frameworks similares, você tem controle cirúrgico sobre cada aspecto do workflow.

## 🎯 Por Que Esta Stack?

```
┌─────────────────────────────────────────────────────────────┐
│  LangChain Approach              │  This Stack               │
├──────────────────────────────────┼──────────────────────────┤
│  Vertical composition            │  Horizontal primitives    │
│  "Use nossa chain pre-built"     │  "Compose como quiser"    │
│  40 níveis de abstração          │  Type-safe, transparent   │
│  Debugging é pesadelo            │  Full observability       │
│  Vendor lock-in disfarçado       │  Zero lock-in             │
└──────────────────────────────────┴───────────────────────────┘
```

**Temporal**: Durable execution - workflows sobrevivem crashes  
**Ray**: Distributed compute - scale horizontally sem boilerplate  
**MLflow**: Experiment tracking - sem dogmas ou limitações

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Temporal Workflow                         │
│  (Orchestration brain - deterministic, observable)           │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    │
│  │  Activity   │ -> │  Activity   │ -> │  Activity   │    │
│  │  Generate   │    │  Train      │    │  Analyze    │    │
│  │  Configs    │    │  Models     │    │  Results    │    │
│  └─────────────┘    └─────────────┘    └─────────────┘    │
│         │                   │                   │           │
└─────────┼───────────────────┼───────────────────┼───────────┘
          │                   │                   │
          v                   v                   v
┌─────────────────┐  ┌──────────────────────┐  ┌─────────────┐
│   Optimizer     │  │    Ray Cluster       │  │   MLflow    │
│  (Adaptive AI)  │  │ ┌────┐ ┌────┐ ┌────┐│  │  (Tracking) │
│                 │  │ │GPU1│ │GPU2│ │GPUn││  │             │
│ • Grid Search   │  │ └────┘ └────┘ └────┘│  │ • Metrics   │
│ • Random        │  │   Stateful Workers   │  │ • Artifacts │
│ • Bayesian      │  │   (Model in memory)  │  │ • Params    │
│ • Evolutionary  │  └──────────────────────┘  └─────────────┘
└─────────────────┘
```

### Key Design Principles

1. **Composable Primitives** - Não chains, mas building blocks
2. **Type Safety** - Pydantic end-to-end, catch errors antes de rodar
3. **Adaptive Logic** - Pipeline aprende e muda estratégia dinamicamente
4. **Full Observability** - Cada step rastreável no Temporal UI + MLflow
5. **Fault Tolerance** - Temporal retry logic + Ray actor resilience

## 🚀 Quick Start

### Prerequisites

```bash
# Python 3.10+
python --version

# Docker & Docker Compose
docker --version
docker-compose --version

# NVIDIA GPU (opcional, mas recomendado)
nvidia-smi
```

### 1. Install Dependencies

```bash
# Core dependencies
pip install \
    temporalio \
    ray[default] \
    mlflow \
    torch \
    transformers \
    datasets \
    scikit-learn \
    scipy \
    pydantic

# Development
pip install pytest black ruff ipython
```

### 2. Start Infrastructure

```bash
# Sobe Temporal + MLflow + PostgreSQL
docker-compose up -d

# Verifica que tá rodando
docker-compose ps

# Acessa UIs:
# - Temporal UI: http://localhost:8088
# - MLflow UI: http://localhost:5000
```

### 3. Start Worker

```bash
# Terminal 1 - Temporal worker
python -m neutron.orchestration.worker

# Você vai ver:
# [INFO] Starting Temporal worker...
# [INFO] Connected to Temporal server
# [INFO] Ray initialized - {'CPU': 8.0, 'GPU': 2.0}
# [INFO] Worker registered and polling for tasks...
```

### 4. Run Pipeline

```bash
# Terminal 2 - Execute pipeline
python -m neutron.cli.main 1  # Basic random search
# ou
python -m neutron.cli.main 2  # Adaptive multi-strategy
# ou
python -m neutron.cli.main 3  # Custom composition

# Or use the installed CLI commands:
neutron 1  # After poetry install
neutron-worker  # Start worker
```

## 📊 Monitoring & Observability

### Temporal UI (http://localhost:8088)

- **Workflows**: Vê cada workflow rodando/completo
- **Timeline**: Visualiza execution path
- **Stack Trace**: Debug workflows em produção
- **Queries**: Inspeciona estado em real-time

### MLflow UI (http://localhost:5000)

- **Experiments**: Agrupa related runs
- **Metrics**: Accuracy, loss, training time
- **Parameters**: Hyperparameters de cada trial
- **Artifacts**: Modelo weights, configs, plots

### Ray Dashboard (http://localhost:8265)

- **Cluster**: CPU/GPU utilization
- **Tasks**: Distributed task execution
- **Actors**: Stateful worker status

## 🎮 Usage Examples

### Example 1: Basic Random Search

```python
config = PipelineConfig(
    experiment_name="my_experiment",
    dataset_path="/path/to/dataset",
    initial_strategy=SearchStrategy.RANDOM,
    max_trials=20,
    max_parallel_trials=4,
)

workflow_id = await start_adaptive_pipeline(config)
```

**Output**:
```
[Pipeline] Strategy: RANDOM
[Iteration 1] Training 4 configs in parallel...
[Run abc123] Completed - Accuracy: 0.8234, Time: 145.3s
[Run def456] Completed - Accuracy: 0.8156, Time: 132.1s
...
[Optimizer] New best score: 0.8234
```

### Example 2: Adaptive Strategy Evolution

```python
config = PipelineConfig(
    experiment_name="adaptive_search",
    initial_strategy=SearchStrategy.GRID,  # Começa conservador
    max_trials=50,
    patience=10,  # Switch se estagna
)
```

**Behavior**:
- Trials 1-15: Grid search (systematic exploration)
- Trial 16: Detecta estagnação → switch pra Random
- Trials 17-35: Random search (broader exploration)
- Trial 36: Melhoria detectada → switch pra Bayesian
- Trials 37-50: Bayesian (exploitation das melhores regiões)

### Example 3: Custom Multi-Phase Workflow

```python
# Fase 1: Quick exploration
phase1_results = await run_pipeline(
    strategy=SearchStrategy.RANDOM,
    max_trials=10
)

# Fase 2: Extract best region
best_config = phase1_results['best_trial']['config']

# Narrow search space
focused_space = HyperparameterSpace(
    learning_rate=(
        best_config.learning_rate * 0.8,
        best_config.learning_rate * 1.2
    ),
    batch_size=[best_config.batch_size],
)

# Fase 3: Fine-grained search
phase2_results = await run_pipeline(
    strategy=SearchStrategy.BAYESIAN,
    hyperparameter_space=focused_space,
    max_trials=30
)
```

## 🔧 Customization Points

### 1. Custom Search Strategies

Adicione sua própria estratégia em `optimizer.py`:

```python
class HyperparameterOptimizer:
    def _my_custom_search(self, num_configs: int, exp_id: str):
        # Sua lógica aqui
        # Exemplo: gradient-based, genetic algorithm, etc
        pass
```

### 2. Custom Metrics

Modifique `compute_metrics` em `trainers.py`:

```python
def compute_metrics(eval_pred):
    # Suas métricas customizadas
    f1 = compute_f1(eval_pred)
    precision = compute_precision(eval_pred)
    
    return {
        "f1": f1,
        "precision": precision,
        "custom_score": f1 * 0.7 + precision * 0.3
    }
```

### 3. Custom Stopping Criteria

Override `_should_early_stop` em `workflows.py`:

```python
async def _should_early_stop(self, state, config):
    # Seu critério customizado
    # Exemplo: para se accuracy > threshold OU time_budget exceeded
    if state.best_score_so_far > 0.95:
        return True
    
    total_time = sum(t.training_time_seconds for t in state.completed_trials)
    if total_time > 3600 * 4:  # 4 hours
        return True
    
    return False
```

### 4. Multi-Objective Optimization

Modifique `TrainingResult.score` em `models.py`:

```python
@property
def score(self) -> float:
    # Pareto optimization
    accuracy_weight = 0.7
    speed_weight = 0.2
    size_weight = 0.1
    
    time_score = 1 - min(self.training_time_seconds / 3600, 1.0)
    
    return (
        self.best_accuracy * accuracy_weight +
        time_score * speed_weight +
        model_size_score * size_weight
    )
```

## 🏭 Production Deployment

### Scaling Considerations

**Temporal Workers**:
```bash
# Run múltiplos workers pra high availability
# Terminal 1
python -m neutron.orchestration.worker --worker-id worker-1

# Terminal 2
python -m neutron.orchestration.worker --worker-id worker-2

# Temporal load-balances automaticamente
```

**Ray Cluster**:
```bash
# Head node
ray start --head --port=6379

# Worker nodes (em outras máquinas)
ray start --address='head_node_ip:6379' --num-gpus=4
```

**MLflow**:
```bash
# Production setup com S3 backend
mlflow server \
  --backend-store-uri postgresql://user:pass@host/mlflow \
  --default-artifact-root s3://my-mlflow-bucket \
  --host 0.0.0.0
```

### Environment Separation

```bash
# Dev
export TEMPORAL_NAMESPACE=dev
export MLFLOW_EXPERIMENT_PREFIX=dev-

# Staging
export TEMPORAL_NAMESPACE=staging
export MLFLOW_EXPERIMENT_PREFIX=staging-

# Prod
export TEMPORAL_NAMESPACE=prod
export MLFLOW_EXPERIMENT_PREFIX=prod-
```

## 🧪 Testing

```bash
# Unit tests
pytest tests/test_optimizer.py -v

# Integration tests (precisa de infrastructure rodando)
pytest tests/test_workflows.py -v

# Load tests
pytest tests/test_scale.py -v --workers=10
```

## 🎓 Learning Path

1. **Start Simple**: Rode Example 1 (basic random search)
2. **Understand Flow**: Olha Temporal UI durante execução
3. **Customize**: Modifique hyperparameter space
4. **Go Adaptive**: Rode Example 2 (multi-strategy)
5. **Compose**: Crie seu próprio multi-phase workflow
6. **Scale**: Deploy em Ray cluster distribuído

## 🔥 Advanced Patterns

### Pattern 1: Ensemble Training

```python
# Train top-K models como ensemble
best_configs = sorted(results, key=lambda x: x.score)[-5:]

ensemble_results = await workflow.execute_child_workflow(
    EnsembleTrainingWorkflow.run,
    args=[best_configs[0], num_models=5]
)
```

### Pattern 2: Transfer Learning Pipeline

```python
# Phase 1: Pretrain on large dataset
pretrain_results = await pretrain_workflow(large_dataset)

# Phase 2: Fine-tune on target dataset
for config in best_configs:
    config.model_path = pretrain_results.best_model_path
    finetune_workflow(config, target_dataset)
```

### Pattern 3: Active Learning Loop

```python
while unlabeled_data:
    # Train model
    results = await train_workflow(labeled_data)
    
    # Select uncertain samples
    uncertain_samples = select_uncertain(model, unlabeled_data)
    
    # Human labeling (external activity)
    new_labels = await request_labels(uncertain_samples)
    
    # Update dataset
    labeled_data.extend(new_labels)
```

## 🐛 Troubleshooting

**Worker not picking up tasks?**
```bash
# Check Temporal connection
temporal workflow list --namespace default

# Verify task queue
temporal task-queue describe --task-queue ml-pipeline-queue
```

**Ray actors crashing?**
```bash
# Check Ray logs
ray logs

# Monitor cluster
ray status
```

**Out of GPU memory?**
```python
# Reduce batch size or enable gradient accumulation
config.batch_size = 16
config.gradient_accumulation_steps = 4  # Effective batch = 64
```

## 📚 Filosofia & Design Decisions

**Why not just use Optuna/Tune?**  
Eles são excelentes pra hyperparameter search, mas não te dão durable orchestration. Se o processo morre, você perde estado. Temporal garante que você pode retomar de onde parou.

**Why Temporal over Airflow?**  
Airflow é DAG-based (static). Temporal permite dynamic workflows que mudam baseado em resultados. Plus, retry logic e versioning são first-class.

**Why Ray over Celery?**  
Ray tem stateful actors (mantém modelo em memória), built-in distributed objects, e melhor GPU support. Celery é task queue, Ray é distributed compute framework.

**Why MLflow over Weights & Biases?**  
MLflow é open-source total, self-hosted, zero vendor lock-in. W&B é incrível mas é SaaS-first. Pra produção enterprise, MLflow te dá controle total.

## 🤝 Contributing

Este é um example framework - fork e customize pra suas necessidades. Algumas ideias pra extensão:

- [ ] Neural Architecture Search integration
- [ ] Multi-GPU data parallelism
- [ ] Kubernetes deployment configs
- [ ] Custom visualization dashboards
- [ ] AutoML wrapper layer
- [ ] Integration com seu PHANTOM/SPECTRE/CEREBRO stack

## 📄 License

MIT - Use como quiser, modifique sem medo, quebra à vontade.

---

**The Bottom Line**: Frameworks tipo LangChain te dão atalhos mas te prendem. Esta stack te dá primitives e liberdade total. É mais work inicial? Sim. Vale a pena? Absolutamente.

*Now go build something that LangChain could never.*
