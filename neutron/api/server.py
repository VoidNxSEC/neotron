from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
import uuid
import logging
from temporalio.client import Client

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neutron.api")

app = FastAPI(title="Neutron Agent API", version="0.1.0")

# Models
class TaskRequest(BaseModel):
    description: str
    metadata: Dict[str, Any] = {}

class TaskResponse(BaseModel):
    task_id: str
    status: str

# Temporal Client Singleton
temporal_client: Optional[Client] = None

@app.on_event("startup")
async def startup_event():
    global temporal_client
    addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    try:
        temporal_client = await Client.connect(addr)
        logger.info(f"Connected to Temporal at {addr}")
    except Exception as e:
        logger.error(f"Failed to connect to Temporal: {e}") 
        # We don't crash, allowing API to start (liveness probe), but endpoints will fail

@app.post("/api/v1/tasks", response_model=TaskResponse)
async def submit_task(task: TaskRequest):
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal backend unavailable")

    workflow_id = f"neutron-task-{uuid.uuid4()}"
    
    try:
        # Trigger AgentCoordinationWorkflow (defined in worker.py)
        handle = await temporal_client.start_workflow(
            "AgentCoordinationWorkflow",
            {"id": workflow_id, "description": task.description, "context": task.metadata},
            id=workflow_id,
            task_queue="neutron-task-queue",
        )
        return TaskResponse(task_id=workflow_id, status="submitted")
    except Exception as e:
        logger.error(f"Workflow submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    if not temporal_client:
        raise HTTPException(status_code=503, detail="Temporal backend unavailable")
        
    try:
        handle = temporal_client.get_workflow_handle(task_id)
        desc = await handle.describe()
        return {
            "task_id": task_id,
            "status": str(desc.status),
            "start_time": desc.start_time,
            "close_time": desc.close_time
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {e}")

@app.get("/health")
async def health():
    return {"status": "ok", "temporal": temporal_client is not None}
