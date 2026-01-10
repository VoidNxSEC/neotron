#!/usr/bin/env python3
"""
DAG Integration Bridge - PHANTOM ↔ Temporal
Filosofia: DAGs são ótimos pra estrutura, Temporal é ótimo pra execução.
          Por que não ter os dois?

Features:
- Convert PHANTOM DAG → Temporal Workflow
- Bi-directional sync (DAG status ← Temporal execution)
- Cost tracking integration
- Dynamic DAG generation from ML results
"""

import json
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import networkx as nx

from temporalio.client import Client
from temporalio import workflow

from models import PipelineConfig, TrainingConfig, HyperparameterSpace, SearchStrategy
from workflows import start_adaptive_pipeline


@dataclass
class DAGTask:
    """Task representation - compatível com PHANTOM"""
    task_id: str
    type: str  # 'ml_training', 'data_prep', 'evaluation', etc
    params: Dict[str, Any]
    dependencies: List[str]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DAG:
    """DAG representation"""
    name: str
    tasks: List[DAGTask]
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "tasks": [t.to_dict() for t in self.tasks],
            "metadata": self.metadata or {}
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DAG':
        return cls(
            name=data["name"],
            tasks=[DAGTask(**t) for t in data["tasks"]],
            metadata=data.get("metadata")
        )
    
    def to_networkx(self) -> nx.DiGraph:
        """Convert to NetworkX graph pra visualização/análise"""
        G = nx.DiGraph()
        
        for task in self.tasks:
            G.add_node(task.task_id, **task.params)
            for dep in task.dependencies:
                G.add_edge(dep, task.task_id)
        
        return G
    
    def validate(self) -> bool:
        """Validate DAG structure (no cycles, all deps exist)"""
        G = self.to_networkx()
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(G):
            raise ValueError("DAG contains cycles!")
        
        # Check all dependencies exist
        task_ids = {t.task_id for t in self.tasks}
        for task in self.tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    raise ValueError(f"Task {task.task_id} depends on non-existent {dep}")
        
        return True


class DAGBridge:
    """Bridge entre PHANTOM DAG e Temporal Workflow"""
    
    def __init__(self, temporal_address: str = "localhost:7233"):
        self.temporal_address = temporal_address
    
    async def convert_dag_to_temporal(
        self, 
        dag: DAG,
        experiment_name: Optional[str] = None
    ) -> str:
        """
        Convert PHANTOM DAG → Temporal Workflow
        
        Returns workflow_id pra tracking
        """
        
        # Validate DAG
        dag.validate()
        
        # Build execution plan baseado em dependencies
        G = dag.to_networkx()
        execution_order = list(nx.topological_sort(G))
        
        print(f"[DAG Bridge] Execution order: {execution_order}")
        
        # Group tasks by level (pra paralelização)
        levels = self._group_by_levels(G)
        
        # Convert ML training tasks to PipelineConfig
        ml_configs = self._extract_ml_configs(dag, experiment_name or dag.name)
        
        # Start workflow
        workflow_id = await start_adaptive_pipeline(ml_configs)
        
        print(f"[DAG Bridge] Started Temporal workflow: {workflow_id}")
        
        return workflow_id
    
    def _group_by_levels(self, G: nx.DiGraph) -> List[List[str]]:
        """
        Group tasks by dependency level
        Tasks no mesmo level podem rodar em paralelo
        """
        levels = []
        remaining = set(G.nodes())
        
        while remaining:
            # Find nodes with no dependencies (or all deps satisfied)
            current_level = []
            for node in remaining:
                deps = set(G.predecessors(node))
                if not deps or not deps.intersection(remaining):
                    current_level.append(node)
            
            if not current_level:
                break  # Shouldn't happen if DAG is valid
            
            levels.append(current_level)
            remaining -= set(current_level)
        
        return levels
    
    def _extract_ml_configs(self, dag: DAG, experiment_name: str) -> PipelineConfig:
        """Extract ML training configs from DAG tasks"""
        
        # Find all ml_training tasks
        ml_tasks = [t for t in dag.tasks if t.type == "ml_training"]
        
        if not ml_tasks:
            raise ValueError("No ml_training tasks in DAG")
        
        # Aggregate hyperparameter space from all tasks
        all_lrs = []
        all_batch_sizes = []
        all_epochs = []
        
        for task in ml_tasks:
            params = task.params
            if "learning_rate" in params:
                lr = params["learning_rate"]
                if isinstance(lr, (list, tuple)):
                    all_lrs.extend(lr)
                else:
                    all_lrs.append(lr)
            
            if "batch_size" in params:
                bs = params["batch_size"]
                if isinstance(bs, (list, tuple)):
                    all_batch_sizes.extend(bs)
                else:
                    all_batch_sizes.append(bs)
            
            if "num_epochs" in params:
                ep = params["num_epochs"]
                if isinstance(ep, (list, tuple)):
                    all_epochs.extend(ep)
                else:
                    all_epochs.append(ep)
        
        # Build hyperparameter space
        space = HyperparameterSpace(
            learning_rate=(min(all_lrs), max(all_lrs)) if all_lrs else (1e-5, 1e-3),
            batch_size=list(set(all_batch_sizes)) if all_batch_sizes else [16, 32, 64],
            num_epochs=(min(all_epochs), max(all_epochs)) if all_epochs else (5, 15),
        )
        
        # Determine strategy from DAG metadata
        strategy = SearchStrategy.RANDOM
        if dag.metadata:
            strategy_str = dag.metadata.get("search_strategy", "random")
            strategy = SearchStrategy[strategy_str.upper()]
        
        # Build PipelineConfig
        config = PipelineConfig(
            experiment_name=experiment_name,
            dataset_path=dag.metadata.get("dataset_path", "/tmp/dataset") if dag.metadata else "/tmp/dataset",
            initial_strategy=strategy,
            hyperparameter_space=space,
            max_trials=len(ml_tasks) * 5,  # 5x number of tasks
            max_parallel_trials=min(4, len(ml_tasks)),
        )
        
        return config
    
    async def generate_dag_from_results(
        self,
        experiment_name: str,
        output_file: str = "generated_dag.json"
    ) -> DAG:
        """
        Reverse: Generate PHANTOM DAG from Temporal results
        Útil pra reproducibility e documentation
        """
        
        import mlflow
        mlflow.set_tracking_uri("http://localhost:5000")
        
        experiment = mlflow.get_experiment_by_name(experiment_name)
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        
        # Create tasks from successful runs
        tasks = []
        for idx, (_, run) in enumerate(runs.iterrows()):
            if run.get("status") == "FINISHED":
                task = DAGTask(
                    task_id=f"train_{run['run_id'][:8]}",
                    type="ml_training",
                    params={
                        "learning_rate": run.get("params.learning_rate"),
                        "batch_size": run.get("params.batch_size"),
                        "num_epochs": run.get("params.num_epochs"),
                        "weight_decay": run.get("params.weight_decay", 0.01),
                    },
                    dependencies=[],  # Independent tasks
                    metadata={
                        "accuracy": run.get("metrics.final_accuracy"),
                        "loss": run.get("metrics.final_loss"),
                        "training_time": run.get("metrics.training_time"),
                        "cost_estimate": run.get("metrics.training_time", 0) / 3600 * 0.90,
                    }
                )
                tasks.append(task)
        
        # Create DAG
        dag = DAG(
            name=f"{experiment_name}_generated",
            tasks=tasks,
            metadata={
                "generated_from": experiment_name,
                "generated_at": datetime.now().isoformat(),
                "total_runs": len(runs),
                "best_accuracy": runs["metrics.final_accuracy"].max(),
            }
        )
        
        # Export
        Path(output_file).write_text(json.dumps(dag.to_dict(), indent=2))
        print(f"[DAG Bridge] Generated DAG exported to {output_file}")
        
        return dag
    
    async def sync_status(
        self,
        workflow_id: str,
        dag_status_file: str = "dag_status.json"
    ):
        """
        Sync Temporal workflow status → PHANTOM DAG status file
        Permite PHANTOM visualizar progresso em real-time
        """
        
        client = await Client.connect(self.temporal_address)
        handle = client.get_workflow_handle(workflow_id)
        
        # Poll workflow status
        desc = await handle.describe()
        
        status = {
            "workflow_id": workflow_id,
            "status": str(desc.status),
            "start_time": desc.start_time.isoformat() if desc.start_time else None,
            "close_time": desc.close_time.isoformat() if desc.close_time else None,
            "execution_time": str(desc.close_time - desc.start_time) if desc.close_time and desc.start_time else None,
        }
        
        # Try to get progress via query
        try:
            progress = await handle.query("get_progress")
            status["progress"] = progress
        except:
            pass
        
        # Write status file
        Path(dag_status_file).write_text(json.dumps(status, indent=2))
        
        return status


class PhantomIntegration:
    """
    High-level integration layer pra PHANTOM
    Handles complete workflow: DAG → Temporal → Results → DAG
    """
    
    def __init__(self):
        self.bridge = DAGBridge()
    
    async def run_phantom_dag(
        self,
        phantom_dag_file: str,
        output_dir: str = "./phantom_results"
    ) -> Dict:
        """
        Complete integration flow:
        1. Load PHANTOM DAG
        2. Convert to Temporal
        3. Execute
        4. Generate result DAG
        5. Export metrics
        """
        
        print(f"[PHANTOM Integration] Loading DAG from {phantom_dag_file}")
        
        # Load DAG
        dag_data = json.loads(Path(phantom_dag_file).read_text())
        dag = DAG.from_dict(dag_data)
        
        print(f"[PHANTOM Integration] DAG: {dag.name}, Tasks: {len(dag.tasks)}")
        
        # Validate
        dag.validate()
        print("[PHANTOM Integration] DAG validation passed ✓")
        
        # Convert and execute
        workflow_id = await self.bridge.convert_dag_to_temporal(dag)
        print(f"[PHANTOM Integration] Workflow started: {workflow_id}")
        
        # Wait for completion (with status updates)
        client = await Client.connect("localhost:7233")
        handle = client.get_workflow_handle(workflow_id)
        
        # Poll status periodically
        while True:
            status = await self.bridge.sync_status(
                workflow_id, 
                f"{output_dir}/status.json"
            )
            
            print(f"[PHANTOM Integration] Status: {status['status']}")
            
            if status["status"] in ["COMPLETED", "FAILED", "TERMINATED"]:
                break
            
            await asyncio.sleep(10)
        
        # Get final results
        result = await handle.result()
        
        # Generate result DAG
        result_dag = await self.bridge.generate_dag_from_results(
            dag.name,
            f"{output_dir}/result_dag.json"
        )
        
        print(f"[PHANTOM Integration] Complete! Results in {output_dir}")
        
        return {
            "workflow_id": workflow_id,
            "original_dag": dag.to_dict(),
            "result_dag": result_dag.to_dict(),
            "temporal_result": result,
            "output_dir": output_dir,
        }


async def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="PHANTOM ↔ Temporal Bridge")
    parser.add_argument("command", choices=[
        "convert", "generate", "sync", "run"
    ])
    parser.add_argument("--dag", "-d", help="PHANTOM DAG file")
    parser.add_argument("--experiment", "-e", help="Experiment name")
    parser.add_argument("--workflow", "-w", help="Temporal workflow ID")
    parser.add_argument("--output", "-o", default="./output", help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "convert":
        if not args.dag:
            print("Error: --dag required")
            return
        
        bridge = DAGBridge()
        dag_data = json.loads(Path(args.dag).read_text())
        dag = DAG.from_dict(dag_data)
        
        workflow_id = await bridge.convert_dag_to_temporal(dag)
        print(f"Workflow started: {workflow_id}")
    
    elif args.command == "generate":
        if not args.experiment:
            print("Error: --experiment required")
            return
        
        bridge = DAGBridge()
        dag = await bridge.generate_dag_from_results(
            args.experiment,
            f"{args.output}/generated_dag.json"
        )
        print(f"DAG generated with {len(dag.tasks)} tasks")
    
    elif args.command == "sync":
        if not args.workflow:
            print("Error: --workflow required")
            return
        
        bridge = DAGBridge()
        status = await bridge.sync_status(
            args.workflow,
            f"{args.output}/status.json"
        )
        print(json.dumps(status, indent=2))
    
    elif args.command == "run":
        if not args.dag:
            print("Error: --dag required")
            return
        
        integration = PhantomIntegration()
        result = await integration.run_phantom_dag(
            args.dag,
            args.output
        )
        
        print("\n" + "="*80)
        print("PHANTOM Integration Complete")
        print("="*80)
        print(f"Workflow ID: {result['workflow_id']}")
        print(f"Original Tasks: {len(result['original_dag']['tasks'])}")
        print(f"Result Tasks: {len(result['result_dag']['tasks'])}")
        print(f"Output: {result['output_dir']}")


if __name__ == "__main__":
    asyncio.run(main())
