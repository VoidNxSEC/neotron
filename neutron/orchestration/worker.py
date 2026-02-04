"""
Neutron Orchestration Worker
Runs Temporal activities and workflows for the Agentic Pipeline.
"""
import asyncio
import logging
import os
from datetime import timedelta
from typing import Dict, Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

# Import our real components
from neutron.agents.cortex import AgentSwarm, Agent, ConsensusStrategy
from neutron.memory.episodic import EpisodicMemory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neutron.worker")

# -----------------------------------------------------------------------------
# Activities
# -----------------------------------------------------------------------------

@activity.defn
async def run_agent_swarm(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity: Execute a task using the Agent Swarm.
    """
    logger.info(f"Activity: run_agent_swarm received task: {task}")
    
    # Initialize agents (in prod, these might be injected or loaded from config)
    agents = [
        Agent(name="Generalist-Alpha", role="planner"),
        Agent(name="Coder-Beta", role="developer"),
        Agent(name="Reviewer-Gamma", role="auditor")
    ]
    
    swarm = AgentSwarm(agents, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)
    result = await swarm.broadcast_task(task)
    
    return result

@activity.defn
async def store_memory_episode(agent_id: str, content: str, meta: Dict[str, Any]) -> int:
    """
    Activity: Persist memory to Synapse (Postgres).
    """
    logger.info(f"Activity: store_memory_episode for {agent_id}")
    
    # Initialize DB connection (connection pooling handles reuse)
    # env var should be provided by systemd/podman
    db_url = os.environ.get("DATABASE_URL", "postgresql://neutron:neutron@localhost:5432/temporal")
    memory = EpisodicMemory(connection_string=db_url)
    
    entry_id = memory.store(agent_id, content, meta=meta)
    return entry_id

# -----------------------------------------------------------------------------
# Workflows
# -----------------------------------------------------------------------------

@workflow.defn
class AgentCoordinationWorkflow:
    @workflow.run
    async def run(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Orchestrates:
        1. Agent Swarm Execution
        2. Compliance Check (Stub for now)
        3. Memory Persistence
        """
        logger.info("Workflow started")
        
        # 1. Run Swarm
        swarm_result = await workflow.execute_activity(
            run_agent_swarm,
            task,
            start_to_close_timeout=timedelta(minutes=5)
        )
        
        # 2. Extract consensus
        consensus = swarm_result.get("consensus", {})
        decision = consensus.get("decision", "No decision")
        
        # 3. Persist to Memory
        await workflow.execute_activity(
            store_memory_episode,
            args=["swarm_consensus", f"Decided: {decision}", {"task_id": task.get("id")}],
            start_to_close_timeout=timedelta(seconds=10)
        )
        
        return swarm_result

# -----------------------------------------------------------------------------
# Main Worker Entrypoint
# -----------------------------------------------------------------------------

async def main():
    logger.info("Starting Neutron Temporal Worker...")
    
    # Connect to Temporal Server
    temporal_addr = os.environ.get("TEMPORAL_ADDRESS", "localhost:7233")
    client = await Client.connect(temporal_addr)
    
    # Create Worker
    worker = Worker(
        client,
        task_queue="neutron-task-queue",
        workflows=[AgentCoordinationWorkflow],
        activities=[run_agent_swarm, store_memory_episode],
    )
    
    logger.info(f"Worker connected to {temporal_addr}. Listening on 'neutron-task-queue'...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())
