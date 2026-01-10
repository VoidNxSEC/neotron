"""
Ray Trainers - Stateful GPU actors for model training

Filosofia: Models are expensive to load - keep them in memory
          Ray actors são stateful - perfeito pra cache de modelos

Features:
- GPU memory management
- Model caching (avoid reloading)
- MLflow integration (logging metrics/artifacts)
- Checkpoint management
- Error handling and retries
"""
import ray
import torch
import mlflow
import time
from typing import List, Optional, Dict
from pathlib import Path
import os

# Hugging Face imports
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    DataCollatorWithPadding
)
from datasets import load_dataset, load_from_disk

from models import TrainingConfig, TrainingResult, MetricResult


# ============================================================================
# Ray Actor - Trainer Pool
# ============================================================================

@ray.remote
class TrainerPool:
    """
    Ray actor pool for parallel training

    Each actor:
    - Owns 1+ GPUs
    - Caches models to avoid reload
    - Logs to MLflow
    - Returns TrainingResult

    Usage:
        pool = TrainerPool.remote(num_gpus=1)
        results = ray.get(pool.train_batch.remote(configs))
    """

    def __init__(self, num_gpus: int = 1):
        """
        Initialize trainer actor

        Args:
            num_gpus: Number of GPUs this actor uses
        """
        self.num_gpus = num_gpus
        self.device = torch.device("cuda" if num_gpus > 0 and torch.cuda.is_available() else "cpu")

        # Model cache {model_name: (model, tokenizer)}
        self.models_cache: Dict[str, tuple] = {}

        # MLflow tracking URI
        self.mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
        mlflow.set_tracking_uri(self.mlflow_uri)

        print(f"✅ TrainerPool initialized")
        print(f"   Device: {self.device}")
        print(f"   GPUs: {num_gpus}")
        print(f"   MLflow: {self.mlflow_uri}")

        if self.device.type == "cuda":
            print(f"   GPU Name: {torch.cuda.get_device_name(0)}")
            print(f"   GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")

    def health_check(self) -> Dict:
        """Health check for actor liveliness"""
        return {
            "status": "healthy",
            "device": str(self.device),
            "gpu_count": self.num_gpus,
            "models_cached": len(self.models_cache)
        }

    def train_batch(self, configs: List[TrainingConfig]) -> List[TrainingResult]:
        """
        Train multiple configs sequentially on this actor's GPU

        Args:
            configs: List of TrainingConfig to train

        Returns:
            List of TrainingResult
        """
        results = []

        for config in configs:
            try:
                result = self._train_single(config)
                results.append(result)
            except Exception as e:
                # Return failed result
                result = TrainingResult(
                    run_id=config.run_id,
                    config=config,
                    metrics=[],
                    best_accuracy=0.0,
                    best_loss=float('inf'),
                    training_time_seconds=0.0,
                    status="failed",
                    error_message=str(e)
                )
                results.append(result)
                print(f"❌ Training failed for {config.run_id}: {e}")

        return results

    def _train_single(self, config: TrainingConfig) -> TrainingResult:
        """
        Train single config

        Flow:
        1. Load model and tokenizer (with caching)
        2. Load dataset
        3. Setup Trainer
        4. Train
        5. Log to MLflow
        6. Return TrainingResult
        """

        start_time = time.time()
        print(f"🏋️  Training {config.run_id}")
        print(f"   Model: {config.model_name}")
        print(f"   LR: {config.learning_rate:.2e}, BS: {config.batch_size}, Epochs: {config.num_epochs}")

        # Step 1: Load model and tokenizer
        model, tokenizer = self._get_or_load_model(config.model_name)

        # Step 2: Load dataset
        dataset = self._load_dataset(config.dataset_path)

        # Step 3: Tokenize dataset
        def tokenize_function(examples):
            return tokenizer(
                examples["text"],
                padding="max_length",
                truncation=True,
                max_length=512
            )

        tokenized_dataset = dataset.map(tokenize_function, batched=True)

        # Step 4: Setup training arguments
        training_args = TrainingArguments(
            output_dir=config.output_dir,
            learning_rate=config.learning_rate,
            per_device_train_batch_size=config.batch_size,
            per_device_eval_batch_size=config.batch_size * 2,
            num_train_epochs=config.num_epochs,
            weight_decay=config.weight_decay,
            warmup_steps=config.warmup_steps,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            logging_strategy="steps",
            logging_steps=50,
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            fp16=config.mixed_precision and self.device.type == "cuda",
            gradient_accumulation_steps=config.gradient_accumulation_steps,
            report_to="none",  # Disable built-in logging, we'll do MLflow manually
            save_total_limit=2,
            seed=42
        )

        # Step 5: Setup Trainer
        data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset["train"],
            eval_dataset=tokenized_dataset.get("validation") or tokenized_dataset.get("test"),
            tokenizer=tokenizer,
            data_collator=data_collator,
            compute_metrics=self._compute_metrics
        )

        # Step 6: Train
        print(f"🚀 Starting training...")
        train_result = trainer.train()

        # Step 7: Evaluate
        eval_results = trainer.evaluate()

        # Step 8: Save model
        output_path = Path(config.output_dir) / config.run_id
        output_path.mkdir(parents=True, exist_ok=True)
        trainer.save_model(str(output_path))

        training_time = time.time() - start_time

        # Step 9: Extract metrics
        best_accuracy = eval_results.get("eval_accuracy", 0.0)
        best_loss = eval_results.get("eval_loss", float('inf'))

        metrics = [
            MetricResult(
                name="final_accuracy",
                value=best_accuracy,
                step=config.num_epochs
            ),
            MetricResult(
                name="final_loss",
                value=best_loss,
                step=config.num_epochs
            ),
            MetricResult(
                name="training_time",
                value=training_time,
                step=config.num_epochs
            )
        ]

        # Step 10: Log to MLflow
        self._log_to_mlflow(config, metrics, str(output_path))

        # Step 11: Create result
        result = TrainingResult(
            run_id=config.run_id,
            config=config,
            metrics=metrics,
            best_accuracy=best_accuracy,
            best_loss=best_loss,
            training_time_seconds=training_time,
            model_path=str(output_path),
            status="success"
        )

        print(f"✅ Training complete!")
        print(f"   Accuracy: {best_accuracy:.4f}")
        print(f"   Loss: {best_loss:.4f}")
        print(f"   Time: {training_time:.1f}s")

        # Clear GPU cache
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

        return result

    def _get_or_load_model(self, model_name: str):
        """
        Get model from cache or load fresh

        Args:
            model_name: HuggingFace model name

        Returns:
            (model, tokenizer) tuple
        """

        if model_name in self.models_cache:
            print(f"📦 Using cached model: {model_name}")
            return self.models_cache[model_name]

        print(f"⬇️  Loading model: {model_name}")

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            num_labels=2  # Binary classification default
        )

        model.to(self.device)

        # Cache it
        self.models_cache[model_name] = (model, tokenizer)

        print(f"✅ Model loaded and cached")
        return model, tokenizer

    def _load_dataset(self, dataset_path: str):
        """
        Load dataset from path or HuggingFace

        Args:
            dataset_path: Path to dataset or HF dataset name

        Returns:
            Dataset object
        """

        if Path(dataset_path).exists():
            # Load from disk
            print(f"📂 Loading dataset from: {dataset_path}")
            dataset = load_from_disk(dataset_path)
        else:
            # Try HuggingFace
            print(f"⬇️  Loading dataset from HuggingFace: {dataset_path}")
            # Default: sentiment analysis dataset
            dataset = load_dataset("imdb" if "imdb" in dataset_path.lower() else dataset_path)

        print(f"✅ Dataset loaded")
        print(f"   Train samples: {len(dataset['train']) if 'train' in dataset else 'N/A'}")

        return dataset

    def _compute_metrics(self, eval_pred):
        """
        Compute metrics for evaluation

        Args:
            eval_pred: EvalPrediction from Trainer

        Returns:
            Dict of metrics
        """
        import numpy as np
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support

        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)

        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average='binary', zero_division=0
        )

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

    def _log_to_mlflow(
        self,
        config: TrainingConfig,
        metrics: List[MetricResult],
        model_path: str
    ):
        """
        Log training to MLflow

        Args:
            config: TrainingConfig
            metrics: List of MetricResult
            model_path: Path to saved model
        """

        try:
            mlflow.set_experiment(config.experiment_id)

            with mlflow.start_run(run_name=config.run_id):
                # Log parameters
                mlflow.log_param("model_name", config.model_name)
                mlflow.log_param("learning_rate", config.learning_rate)
                mlflow.log_param("batch_size", config.batch_size)
                mlflow.log_param("num_epochs", config.num_epochs)
                mlflow.log_param("weight_decay", config.weight_decay)
                mlflow.log_param("warmup_steps", config.warmup_steps)
                mlflow.log_param("use_gpu", config.use_gpu)
                mlflow.log_param("mixed_precision", config.mixed_precision)

                # Log metrics
                for metric in metrics:
                    mlflow.log_metric(metric.name, metric.value, step=metric.step)

                # Log model artifacts (optional, can be large)
                # mlflow.log_artifacts(model_path, artifact_path="model")

                print(f"📊 Logged to MLflow: {config.experiment_id}/{config.run_id}")

        except Exception as e:
            print(f"⚠️  MLflow logging failed: {e}")
            # Don't fail training if logging fails

    def clear_cache(self):
        """Clear model cache to free memory"""
        self.models_cache.clear()
        if self.device.type == "cuda":
            torch.cuda.empty_cache()
        print("🗑️  Model cache cleared")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_trainer_pool(num_gpus: int = 1, num_actors: int = 1) -> List:
    """
    Create pool of trainer actors

    Args:
        num_gpus: GPUs per actor
        num_actors: Number of actors to create

    Returns:
        List of actor handles
    """

    pools = []
    for i in range(num_actors):
        pool = TrainerPool.options(
            name=f"trainer_pool_{i}",
            num_gpus=num_gpus
        ).remote(num_gpus=num_gpus)
        pools.append(pool)

    print(f"✅ Created {num_actors} trainer pools (GPUs per pool: {num_gpus})")
    return pools
