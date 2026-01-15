"""
Neutron ML Pipeline - Training Functions

Ray-based distributed training functions for hyperparameter trials.
Phase 1 MVP: Uses sklearn classifier for fast testing.
Phase 4: Will be upgraded to Transformers (DistilBERT).
"""

import time
import ray
import mlflow
from typing import Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.pipeline import Pipeline


@ray.remote(num_cpus=2)
def train_model_ray(
    hyperparameters: Dict[str, Any],
    dataset_path: str,
    experiment_name: str,
    mlflow_uri: str
) -> Dict[str, Any]:
    """
    Train model with given hyperparameters on Ray worker.

    Phase 1 MVP: Uses sklearn SGDClassifier with TF-IDF features
    Phase 4: Will use Transformers DistilBERT

    Args:
        hyperparameters: Dictionary with learning_rate, batch_size, num_epochs, etc.
        dataset_path: Path to dataset (e.g., "imdb")
        experiment_name: MLflow experiment name
        mlflow_uri: MLflow tracking server URI

    Returns:
        Dictionary with metrics and mlflow_run_id
    """
    start_time = time.time()

    try:
        # Set MLflow tracking
        mlflow.set_tracking_uri(mlflow_uri)
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run() as run:
            # Log hyperparameters
            mlflow.log_params(hyperparameters)

            # Load dataset
            if dataset_path == "imdb":
                train_texts, train_labels, eval_texts, eval_labels = load_imdb_dataset()
            else:
                # Custom dataset loading (for future phases)
                raise NotImplementedError(f"Dataset {dataset_path} not supported yet")

            # Build sklearn pipeline
            model = Pipeline([
                ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
                ('clf', SGDClassifier(
                    loss='log_loss',  # Logistic regression
                    alpha=hyperparameters.get("weight_decay", 0.0001),
                    learning_rate='constant',
                    eta0=hyperparameters.get("learning_rate", 0.01),
                    max_iter=hyperparameters.get("num_epochs", 5) * 100,  # Approximate epochs
                    random_state=42,
                    n_jobs=1
                ))
            ])

            # Train
            model.fit(train_texts, train_labels)

            # Evaluate on training set
            train_pred = model.predict(train_texts)
            train_accuracy = accuracy_score(train_labels, train_pred)
            train_f1 = f1_score(train_labels, train_pred, average='binary')

            # Evaluate on validation set
            eval_pred = model.predict(eval_texts)
            eval_accuracy = accuracy_score(eval_labels, eval_pred)
            eval_f1 = f1_score(eval_labels, eval_pred, average='binary')

            # Calculate loss approximation (negative log likelihood proxy)
            from sklearn.metrics import log_loss
            try:
                train_proba = model.predict_proba(train_texts)
                eval_proba = model.predict_proba(eval_texts)
                train_loss = log_loss(train_labels, train_proba)
                eval_loss = log_loss(eval_labels, eval_proba)
            except AttributeError:
                # If predict_proba not available, use dummy loss
                train_loss = 1.0 - train_accuracy
                eval_loss = 1.0 - eval_accuracy

            # Log metrics
            metrics = {
                "val_accuracy": eval_accuracy,
                "val_f1": eval_f1,
                "val_loss": eval_loss,
                "train_accuracy": train_accuracy,
                "train_f1": train_f1,
                "train_loss": train_loss
            }

            mlflow.log_metrics(metrics)

            duration = time.time() - start_time
            mlflow.log_metric("duration_seconds", duration)

            return {
                "metrics": metrics,
                "mlflow_run_id": run.info.run_id,
                "status": "completed",
                "duration_seconds": duration
            }

    except Exception as e:
        # Log error to MLflow if possible
        duration = time.time() - start_time
        try:
            mlflow.log_param("error", str(e))
        except:
            pass

        return {
            "metrics": {},
            "mlflow_run_id": "",
            "status": "failed",
            "duration_seconds": duration,
            "error_message": str(e)
        }


def load_imdb_dataset(train_size: int = 5000, eval_size: int = 1000):
    """
    Load IMDB dataset for sentiment classification.

    Phase 1 MVP: Uses HuggingFace datasets library
    Returns subset for fast experimentation.

    Args:
        train_size: Number of training samples
        eval_size: Number of evaluation samples

    Returns:
        Tuple of (train_texts, train_labels, eval_texts, eval_labels)
    """
    try:
        from datasets import load_dataset

        # Load IMDB dataset
        dataset = load_dataset("imdb")

        # Get subsets
        train_data = dataset["train"].select(range(min(train_size, len(dataset["train"]))))
        eval_data = dataset["test"].select(range(min(eval_size, len(dataset["test"]))))

        # Extract texts and labels
        train_texts = train_data["text"]
        train_labels = train_data["label"]
        eval_texts = eval_data["text"]
        eval_labels = eval_data["label"]

        return train_texts, train_labels, eval_texts, eval_labels

    except Exception as e:
        # Fallback: Return dummy data for testing
        print(f"Warning: Could not load IMDB dataset: {e}")
        print("Using dummy data for testing")

        train_texts = [
            "This movie was great! I loved it.",
            "Terrible film, waste of time.",
            "Amazing performance by the actors.",
            "Boring and predictable plot."
        ] * (train_size // 4)

        train_labels = [1, 0, 1, 0] * (train_size // 4)

        eval_texts = [
            "Excellent movie, highly recommend!",
            "Awful, couldn't even finish it."
        ] * (eval_size // 2)

        eval_labels = [1, 0] * (eval_size // 2)

        return train_texts, train_labels, eval_texts, eval_labels
