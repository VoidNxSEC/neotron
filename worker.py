#!/usr/bin/env python3
"""
Temporal Worker - O executor que roda activities e workflows

Filosofia: Workers são stateless (Temporal mantém estado), mas precisam de Ray cluster
          Workers podem crashar - Temporal vai redistribuir o trabalho

Features:
- Connects to Temporal server
- Initializes Ray cluster (local or distributed)
- Registers workflows and activities
- Graceful shutdown on SIGTERM/SIGINT
- Health checks and monitoring
"""
import asyncio
import signal
import sys
import os
from typing import Optional
import logging

# Temporal imports
from temporalio.client import Client
from temporalio.worker import Worker

# Ray imports
import ray

# Neutron imports
from workflows import (
    AdaptiveMLPipelineWorkflow,
    EnsembleTrainingWorkflow,
    AdaptiveMLPipelineWithQueries,
    train_model_batch_activity,
    setup_mlflow_activity,
    analyze_results_activity,
    validate_gcp_credits_activity  # CEREBRO integration
)
from trainers import TrainerPool


# ============================================================================
# Configuration
# ============================================================================

# Temporal config
TEMPORAL_ADDRESS = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
TEMPORAL_NAMESPACE = os.getenv("TEMPORAL_NAMESPACE", "default")
TASK_QUEUE = os.getenv("TASK_QUEUE", "ml-pipeline-queue")

# Ray config
RAY_ADDRESS = os.getenv("RAY_ADDRESS")  # None = local mode, "auto" = connect to cluster
RAY_NUM_CPUS = int(os.getenv("RAY_NUM_CPUS", "0"))  # 0 = all available
RAY_NUM_GPUS = int(os.getenv("RAY_NUM_GPUS", "1"))

# Worker config
MAX_CONCURRENT_ACTIVITIES = int(os.getenv("MAX_CONCURRENT_ACTIVITIES", "10"))
MAX_CONCURRENT_WORKFLOWS = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "5"))

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("worker.log")
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# Ray Initialization
# ============================================================================

def initialize_ray() -> None:
    """
    Initialize Ray cluster

    Modes:
    - Local: RAY_ADDRESS=None (default)
    - Cluster: RAY_ADDRESS="auto" or "ray://head_node:10001"
    """

    if ray.is_initialized():
        logger.info("Ray already initialized")
        return

    try:
        if RAY_ADDRESS:
            # Connect to existing cluster
            logger.info(f"🔗 Connecting to Ray cluster: {RAY_ADDRESS}")
            ray.init(
                address=RAY_ADDRESS,
                namespace="neutron",
                ignore_reinit_error=True
            )
        else:
            # Start local Ray
            logger.info("🚀 Starting local Ray cluster")
            ray.init(
                num_cpus=RAY_NUM_CPUS if RAY_NUM_CPUS > 0 else None,
                num_gpus=RAY_NUM_GPUS,
                namespace="neutron",
                ignore_reinit_error=True,
                include_dashboard=True,
                dashboard_port=8265
            )

        # Print cluster info
        resources = ray.available_resources()
        logger.info("✅ Ray initialized successfully")
        logger.info(f"   CPUs: {resources.get('CPU', 0)}")
        logger.info(f"   GPUs: {resources.get('GPU', 0)}")
        logger.info(f"   Memory: {resources.get('memory', 0) / 1e9:.2f} GB")

        if not RAY_ADDRESS:
            logger.info(f"   Dashboard: http://localhost:8265")

    except Exception as e:
        logger.error(f"❌ Failed to initialize Ray: {e}")
        raise


def shutdown_ray() -> None:
    """Gracefully shutdown Ray"""
    if ray.is_initialized():
        logger.info("🛑 Shutting down Ray cluster...")
        ray.shutdown()
        logger.info("✅ Ray shutdown complete")


# ============================================================================
# Temporal Worker
# ============================================================================

class NeutronWorker:
    """
    Neutron Temporal Worker

    Responsibilities:
    - Connect to Temporal
    - Register workflows and activities
    - Run worker loop
    - Handle graceful shutdown
    """

    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.shutdown_event = asyncio.Event()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        sig_name = signal.Signals(signum).name
        logger.info(f"🛑 Received {sig_name}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def connect(self) -> None:
        """Connect to Temporal server"""
        logger.info(f"🔗 Connecting to Temporal: {TEMPORAL_ADDRESS}")

        try:
            self.client = await Client.connect(
                TEMPORAL_ADDRESS,
                namespace=TEMPORAL_NAMESPACE
            )
            logger.info(f"✅ Connected to Temporal (namespace: {TEMPORAL_NAMESPACE})")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Temporal: {e}")
            raise

    async def create_worker(self) -> None:
        """Create Temporal worker with workflows and activities"""
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")

        logger.info(f"👷 Creating worker for task queue: {TASK_QUEUE}")

        # All workflows
        workflows = [
            AdaptiveMLPipelineWorkflow,
            EnsembleTrainingWorkflow,
            AdaptiveMLPipelineWithQueries
        ]

        # All activities
        activities = [
            train_model_batch_activity,
            setup_mlflow_activity,
            analyze_results_activity,
            validate_gcp_credits_activity  # CEREBRO credit validation
        ]

        self.worker = Worker(
            self.client,
            task_queue=TASK_QUEUE,
            workflows=workflows,
            activities=activities,
            max_concurrent_workflow_tasks=MAX_CONCURRENT_WORKFLOWS,
            max_concurrent_activities=MAX_CONCURRENT_ACTIVITIES,
        )

        logger.info(f"✅ Worker created")
        logger.info(f"   Workflows: {len(workflows)}")
        logger.info(f"   Activities: {len(activities)}")
        logger.info(f"   Max concurrent workflows: {MAX_CONCURRENT_WORKFLOWS}")
        logger.info(f"   Max concurrent activities: {MAX_CONCURRENT_ACTIVITIES}")

    async def run(self) -> None:
        """Run worker loop until shutdown signal"""
        if not self.worker:
            raise RuntimeError("Worker not created. Call create_worker() first.")

        logger.info("🏃 Worker running and polling for tasks...")
        logger.info("   Press Ctrl+C to stop")
        logger.info("")

        # Run worker until shutdown
        try:
            await asyncio.gather(
                self.worker.run(),
                self._wait_for_shutdown()
            )
        except asyncio.CancelledError:
            logger.info("Worker task cancelled")

    async def _wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self.shutdown_event.wait()
        logger.info("Shutdown signal received, stopping worker...")

    async def shutdown(self):
        """Gracefully shutdown worker"""
        logger.info("🛑 Shutting down worker...")

        if self.worker:
            await self.worker.shutdown()
            logger.info("✅ Worker shutdown complete")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """
    Main worker process

    Flow:
    1. Initialize Ray cluster
    2. Create trainer pool actors
    3. Connect to Temporal
    4. Create and run worker
    5. Graceful shutdown on signal
    """

    logger.info("="*80)
    logger.info("  🚀 Neutron ML Pipeline Worker")
    logger.info("="*80)
    logger.info("")

    # Step 1: Initialize Ray
    initialize_ray()

    # Step 2: Create trainer pool (Ray actor)
    logger.info("🎯 Creating trainer pool...")
    try:
        # Create pool with specified GPU count
        # This actor will be used by train_model_batch_activity
        trainer_pool = TrainerPool.options(
            name="trainer_pool",  # Named actor, can be accessed globally
            num_gpus=RAY_NUM_GPUS,
            max_concurrency=MAX_CONCURRENT_ACTIVITIES
        ).remote(num_gpus=RAY_NUM_GPUS)

        # Test that actor is alive
        ray.get(trainer_pool.health_check.remote())
        logger.info(f"✅ Trainer pool created (GPUs: {RAY_NUM_GPUS})")

    except Exception as e:
        logger.error(f"❌ Failed to create trainer pool: {e}")
        shutdown_ray()
        sys.exit(1)

    # Step 3: Create Temporal worker
    worker = NeutronWorker()

    try:
        # Connect to Temporal
        await worker.connect()

        # Create worker
        await worker.create_worker()

        # Run worker loop
        await worker.run()

    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received")
    except Exception as e:
        logger.error(f"❌ Worker error: {e}", exc_info=True)
    finally:
        # Cleanup
        await worker.shutdown()
        shutdown_ray()
        logger.info("")
        logger.info("="*80)
        logger.info("  👋 Worker shutdown complete")
        logger.info("="*80)


if __name__ == "__main__":
    # Run async main
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
