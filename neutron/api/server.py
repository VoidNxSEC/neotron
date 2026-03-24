from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from temporalio.client import Client

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neutron.api")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
API_SECRET_KEY: str | None = os.getenv("API_SECRET_KEY")
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "*").split(",")
    if o.strip()
]
JWT_EXPIRATION_SECONDS: int = int(os.getenv("JWT_EXPIRATION_SECONDS", "3600"))

AVAILABLE_AGENTS: list[dict[str, str]] = [
    {"agent_id": "compliance_analyst", "description": "Regulatory compliance analysis agent"},
    {"agent_id": "risk_assessor", "description": "Risk assessment and scoring agent"},
    {"agent_id": "decision_maker", "description": "Decision synthesis and recommendation agent"},
]
AGENT_IDS: set[str] = {a["agent_id"] for a in AVAILABLE_AGENTS}

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

# -- Error models -----------------------------------------------------------

class ErrorDetail(BaseModel):
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    status_code: int


class ErrorResponse(BaseModel):
    error: ErrorDetail


# -- Auth models ------------------------------------------------------------

class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# -- Task models (existing) -------------------------------------------------

class TaskRequest(BaseModel):
    description: str
    metadata: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    task_id: str
    status: str


# -- Agent models -----------------------------------------------------------

class AgentInfo(BaseModel):
    agent_id: str
    description: str


class AgentExecuteRequest(BaseModel):
    agent_id: str
    task_type: str
    input: Dict[str, Any] = {}


class AgentExecuteResponse(BaseModel):
    execution_id: str
    agent_id: str
    status: str
    result: Dict[str, Any] = {}


class SwarmExecuteRequest(BaseModel):
    agent_ids: List[str]
    task_type: str
    input: Dict[str, Any] = {}
    consensus_strategy: str = "majority"


class SwarmExecuteResponse(BaseModel):
    swarm_id: str
    agent_ids: List[str]
    status: str
    consensus_strategy: str
    results: Dict[str, Any] = {}


class ComplianceStatus(BaseModel):
    status: str
    agents_available: int
    last_check: str
    issues: List[str] = []


# ---------------------------------------------------------------------------
# JWT helpers (stdlib only -- HMAC-SHA256)
# ---------------------------------------------------------------------------

def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _jwt_sign(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    segments: list[str] = [
        _b64url_encode(json.dumps(header, separators=(",", ":")).encode()),
        _b64url_encode(json.dumps(payload, separators=(",", ":")).encode()),
    ]
    signing_input = f"{segments[0]}.{segments[1]}".encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url_encode(signature))
    return ".".join(segments)


def _jwt_verify(token: str, secret: str) -> dict:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token structure")
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(parts[2])
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Invalid signature")
    payload = json.loads(_b64url_decode(parts[1]))
    if "exp" in payload and payload["exp"] < time.time():
        raise ValueError("Token expired")
    return payload


# ---------------------------------------------------------------------------
# Rate limiter -- in-memory token bucket (per IP)
# ---------------------------------------------------------------------------

class _TokenBucket:
    """Simple token-bucket rate limiter. Thread-safe enough for async."""

    def __init__(self, rate: float, capacity: int) -> None:
        self.rate = rate          # tokens per second
        self.capacity = capacity  # max burst
        self._buckets: dict[str, tuple[float, float]] = {}  # ip -> (tokens, last_ts)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        tokens, last = self._buckets.get(key, (float(self.capacity), now))
        elapsed = now - last
        tokens = min(self.capacity, tokens + elapsed * self.rate)
        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            return True
        self._buckets[key] = (tokens, now)
        return False


# 60 requests / 60 seconds = 1 token/sec, burst capacity 60
_rate_limiter = _TokenBucket(rate=1.0, capacity=60)

# ---------------------------------------------------------------------------
# Error helper
# ---------------------------------------------------------------------------

def _error_response(status_code: int, message: str, correlation_id: str | None = None) -> JSONResponse:
    cid = correlation_id or str(uuid.uuid4())
    body = ErrorResponse(
        error=ErrorDetail(correlation_id=cid, message=message, status_code=status_code)
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(application: FastAPI):
    # -- startup --
    global _temporal_client
    addr = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    try:
        _temporal_client = await Client.connect(addr)
        logger.info("Connected to Temporal at %s", addr)
    except Exception as e:
        logger.error("Failed to connect to Temporal: %s", e)
        # Allow API to start (liveness probe), but endpoints will return 503
    yield
    # -- shutdown --
    _temporal_client = None


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

_temporal_client: Client | None = None

app = FastAPI(
    title="Neutron Agent API",
    version="0.2.0",
    lifespan=lifespan,
)

# -- CORS -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -- Include routers --------------------------------------------------------
from neutron.api.compliance import router as compliance_router
from neutron.api.auth_endpoints import router as auth_router
from neutron.api.policy_endpoints import router as policy_router
from neutron.api.audit_endpoints import router as audit_router
from neutron.api.consent_endpoints import router as consent_router
from neutron.api.oracle_endpoints import router as oracle_router

app.include_router(auth_router)
app.include_router(policy_router)
app.include_router(audit_router)
app.include_router(consent_router)
app.include_router(compliance_router)
app.include_router(oracle_router)


# -- Rate-limit middleware --------------------------------------------------

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    if not _rate_limiter.allow(client_ip):
        return _error_response(429, "Rate limit exceeded. Max 60 requests per minute.")
    response = await call_next(request)
    return response


# ---------------------------------------------------------------------------
# Auth dependency (imported from auth module)
# ---------------------------------------------------------------------------

from neutron.api.auth import get_current_user, AuthPrincipal

# Legacy compatibility - map old require_auth to new get_current_user
require_auth = get_current_user


# ---------------------------------------------------------------------------
# Endpoints -- Health (no auth)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "temporal": _temporal_client is not None}


# ---------------------------------------------------------------------------
# Endpoints -- Tasks (existing, now auth-protected)
# ---------------------------------------------------------------------------

@app.post("/api/v1/tasks", response_model=TaskResponse)
async def submit_task(task: TaskRequest, _user: AuthPrincipal = Depends(require_auth)):
    if not _temporal_client:
        raise HTTPException(status_code=503, detail="Temporal backend unavailable")

    correlation_id = str(uuid.uuid4())
    workflow_id = f"neutron-task-{uuid.uuid4()}"

    try:
        await _temporal_client.start_workflow(
            "AgentCoordinationWorkflow",
            {"id": workflow_id, "description": task.description, "context": task.metadata},
            id=workflow_id,
            task_queue="neutron-task-queue",
        )
        return TaskResponse(task_id=workflow_id, status="submitted")
    except Exception as e:
        logger.error("Workflow submission failed [%s]: %s", correlation_id, e)
        return _error_response(500, f"Workflow submission failed: {e}", correlation_id)


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str, _user: AuthPrincipal = Depends(require_auth)):
    if not _temporal_client:
        raise HTTPException(status_code=503, detail="Temporal backend unavailable")

    try:
        handle = _temporal_client.get_workflow_handle(task_id)
        desc = await handle.describe()
        return {
            "task_id": task_id,
            "status": str(desc.status),
            "start_time": desc.start_time,
            "close_time": desc.close_time,
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {e}")


# ---------------------------------------------------------------------------
# Endpoints -- Agents
# ---------------------------------------------------------------------------

@app.get("/api/v1/agents", response_model=List[AgentInfo])
async def list_agents(_user: AuthPrincipal = Depends(require_auth)):
    """Return the list of available agents."""
    return [AgentInfo(**a) for a in AVAILABLE_AGENTS]


@app.post("/api/v1/agents/execute", response_model=AgentExecuteResponse)
async def execute_agent(body: AgentExecuteRequest, _user: AuthPrincipal = Depends(require_auth)):
    """Execute a single agent task with real LLM backend."""
    if body.agent_id not in AGENT_IDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent_id '{body.agent_id}'. Available: {sorted(AGENT_IDS)}",
        )

    execution_id = f"agent-exec-{uuid.uuid4()}"
    logger.info("Agent execution requested: agent=%s task_type=%s id=%s", body.agent_id, body.task_type, execution_id)

    from neutron.agents.cortex import Agent

    agent_prompts = {
        "compliance_analyst": "You are an LGPD/GDPR compliance expert. Analyze regulatory compliance.",
        "risk_assessor": "You are a risk assessment specialist. Evaluate risks and regulatory exposure.",
        "decision_maker": "You are a decision synthesizer. Make a final APPROVED/REJECTED/CONDITIONAL decision.",
    }

    agent = Agent(
        name=body.agent_id,
        role=body.agent_id.replace("_", " "),
        system_prompt=agent_prompts.get(body.agent_id, "You are a helpful AI agent."),
    )

    task = {"type": body.task_type, "description": f"Execute {body.task_type}", "data": body.input}

    try:
        response = await agent.execute(task)
        return AgentExecuteResponse(
            execution_id=execution_id,
            agent_id=body.agent_id,
            status="completed",
            result={
                "content": response.content,
                "confidence": response.confidence,
                "metadata": response.metadata,
            },
        )
    except Exception as e:
        logger.error("Agent execution failed [%s]: %s", execution_id, e)
        return AgentExecuteResponse(
            execution_id=execution_id,
            agent_id=body.agent_id,
            status="error",
            result={"error": str(e)},
        )


# ---------------------------------------------------------------------------
# Endpoints -- Swarm
# ---------------------------------------------------------------------------

@app.post("/api/v1/swarm/execute", response_model=SwarmExecuteResponse)
async def execute_swarm(body: SwarmExecuteRequest, _user: AuthPrincipal = Depends(require_auth)):
    """Execute an agent swarm with consensus."""
    unknown = set(body.agent_ids) - AGENT_IDS
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent_id(s): {sorted(unknown)}. Available: {sorted(AGENT_IDS)}",
        )

    if not body.agent_ids:
        raise HTTPException(status_code=400, detail="agent_ids must not be empty")

    valid_strategies = {"majority", "unanimous", "weighted", "first"}
    if body.consensus_strategy not in valid_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid consensus_strategy '{body.consensus_strategy}'. Valid: {sorted(valid_strategies)}",
        )

    swarm_id = f"swarm-{uuid.uuid4()}"
    logger.info(
        "Swarm execution requested: agents=%s strategy=%s id=%s",
        body.agent_ids, body.consensus_strategy, swarm_id,
    )

    from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy

    strategy_map = {
        "majority": ConsensusStrategy.MAJORITY_VOTE,
        "unanimous": ConsensusStrategy.UNANIMOUS,
        "weighted": ConsensusStrategy.WEIGHTED_CONFIDENCE,
        "first": ConsensusStrategy.DICTATOR,
    }

    agent_prompts = {
        "compliance_analyst": "You are an LGPD/GDPR compliance expert. Analyze regulatory compliance.",
        "risk_assessor": "You are a risk assessment specialist. Evaluate risks and regulatory exposure.",
        "decision_maker": "You are a decision synthesizer. Make a final APPROVED/REJECTED/CONDITIONAL decision.",
    }

    agents = [
        Agent(
            name=agent_id,
            role=agent_id.replace("_", " "),
            system_prompt=agent_prompts.get(agent_id, "You are a helpful AI agent."),
        )
        for agent_id in body.agent_ids
    ]

    swarm = AgentSwarm(
        agents=agents,
        consensus_strategy=strategy_map[body.consensus_strategy],
    )

    task = {
        "type": body.task_type,
        "description": f"Execute {body.task_type}",
        "data": body.input,
    }

    try:
        result = await swarm.broadcast_task(task)
        return SwarmExecuteResponse(
            swarm_id=swarm_id,
            agent_ids=body.agent_ids,
            status="completed",
            consensus_strategy=body.consensus_strategy,
            results={
                "consensus": result["consensus"],
                "individual_results": result["individual_results"],
            },
        )
    except Exception as e:
        logger.error("Swarm execution failed [%s]: %s", swarm_id, e)
        return SwarmExecuteResponse(
            swarm_id=swarm_id,
            agent_ids=body.agent_ids,
            status="error",
            consensus_strategy=body.consensus_strategy,
            results={"error": str(e)},
        )


# ---------------------------------------------------------------------------
# Endpoints -- Compliance
# ---------------------------------------------------------------------------

@app.get("/api/v1/compliance/status", response_model=ComplianceStatus)
async def compliance_status(_user: AuthPrincipal = Depends(require_auth)):
    """Return a compliance status summary."""
    import datetime

    return ComplianceStatus(
        status="operational",
        agents_available=len(AVAILABLE_AGENTS),
        last_check=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        issues=[],
    )


# ---------------------------------------------------------------------------
# Endpoints -- Metrics
# ---------------------------------------------------------------------------


class CortexTestRequest(BaseModel):
    agent_ids: List[str] = ["compliance_analyst", "risk_assessor", "decision_maker"]
    task: str = "Evaluate compliance for a credit scoring decision"
    data: Dict[str, Any] = {}
    consensus_strategy: str = "weighted"


@app.get("/v1/metrics")
async def get_metrics(_user: AuthPrincipal = Depends(require_auth)):
    """Return LLM client health, circuit breaker status, and basic metrics."""
    try:
        try:
            from mlops.llm.client import LLMClient
        except ImportError:
            from neutron.agents._llm_http_client import LLMHTTPClient as LLMClient

        client = LLMClient()
        health = await client.health_check()
        cb_status = client.get_circuit_breaker_status()

        return {
            "status": "ok",
            "providers": health,
            "circuit_breakers": cb_status,
            "agents_available": len(AVAILABLE_AGENTS),
        }
    except Exception as e:
        logger.error("Metrics collection failed: %s", e)
        return {
            "status": "degraded",
            "error": str(e),
            "agents_available": len(AVAILABLE_AGENTS),
        }


# ---------------------------------------------------------------------------
# Endpoints -- Cortex Test
# ---------------------------------------------------------------------------

@app.post("/v1/test/cortex")
async def test_cortex(body: CortexTestRequest, _user: AuthPrincipal = Depends(require_auth)):
    """
    Test multi-agent consensus without the full 4-layer compliance flow.

    Useful for verifying LLM connectivity and agent behavior.
    """
    from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy

    strategy_map = {
        "majority": ConsensusStrategy.MAJORITY_VOTE,
        "unanimous": ConsensusStrategy.UNANIMOUS,
        "weighted": ConsensusStrategy.WEIGHTED_CONFIDENCE,
        "first": ConsensusStrategy.DICTATOR,
    }

    strategy = strategy_map.get(body.consensus_strategy, ConsensusStrategy.WEIGHTED_CONFIDENCE)

    unknown = set(body.agent_ids) - AGENT_IDS
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent_id(s): {sorted(unknown)}. Available: {sorted(AGENT_IDS)}",
        )

    agent_prompts = {
        "compliance_analyst": "You are an LGPD/GDPR compliance expert. Analyze regulatory compliance.",
        "risk_assessor": "You are a risk assessment specialist. Evaluate risks and regulatory exposure.",
        "decision_maker": "You are a decision synthesizer. Make a final APPROVED/REJECTED/CONDITIONAL decision.",
    }

    agents = [
        Agent(
            name=agent_id,
            role=agent_id.replace("_", " "),
            system_prompt=agent_prompts.get(agent_id, "You are a helpful AI agent."),
        )
        for agent_id in body.agent_ids
    ]

    swarm = AgentSwarm(agents=agents, consensus_strategy=strategy)

    task = {
        "type": "cortex_test",
        "description": body.task,
        "data": body.data,
    }

    try:
        result = await swarm.broadcast_task(task)
        return {
            "status": "completed",
            "consensus": result["consensus"],
            "individual_results": result["individual_results"],
            "agents_used": body.agent_ids,
        }
    except Exception as e:
        logger.error("Cortex test failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Cortex test failed: {str(e)}")
