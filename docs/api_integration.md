# NEXUS API Integration Guide

Base URL: `http://localhost:8000`

## Authentication

Most endpoints require JWT authentication. The compliance validation endpoint (`/v1/compliance/validate`) and ORACLE endpoint (`/v1/oracle/explain`) are accessible without auth for pilot testing.

### Get a Token

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Use the returned `access_token` in subsequent requests:
```
Authorization: Bearer <access_token>
```

## Endpoints

### Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Service health check |

### Compliance (4-Layer NEXUS Flow)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/compliance/validate` | No | Execute 4-layer compliance validation |
| GET | `/v1/compliance/policies` | No | List supported regulations |
| GET | `/v1/compliance/health` | No | Compliance system health |
| GET | `/v1/compliance/audit/{hash}` | No | Retrieve audit log by hash |

#### POST /v1/compliance/validate

Execute the full SENTINEL -> BASTION -> CORTEX -> AUDIT flow.

**Request:**
```json
{
  "customer_id": "customer_123",
  "action": "loan_approval",
  "data": {
    "credit_score": 720,
    "amount": 10000
  },
  "consent_token": "lgpd_consent_abc123",
  "regulation": "LGPD",
  "metadata": {}
}
```

**Response:**
```json
{
  "request_id": "uuid",
  "decision": "approved",
  "confidence": 0.85,
  "explanation": "Consensus Decision: APPROVED\n...",
  "audit_hash": "sha256...",
  "layers": {
    "SENTINEL": {"layer_name": "SENTINEL", "passed": true, "status": "PASS", ...},
    "BASTION": {"layer_name": "BASTION", "passed": true, "status": "ENFORCED", ...},
    "CORTEX": {"layer_name": "CORTEX", "passed": true, "status": "APPROVED", ...},
    "AUDIT": {"layer_name": "AUDIT", "passed": true, "status": "LOGGED", ...}
  },
  "total_processing_time_ms": 2500.0,
  "timestamp": 1739577600.0
}
```

#### GET /v1/compliance/audit/{audit_hash}

Retrieve a stored audit log by its hash (IPFS CID, Arweave TX, or local hash).

**Response (found):**
```json
{
  "audit_hash": "abc123...",
  "status": "found",
  "storage_type": "local",
  "log": {
    "log_id": "uuid",
    "user_address": "customer_123",
    "regulation": "LGPD",
    "article": 7,
    "action": "loan_approval:approved",
    "passed": true,
    "timestamp": 1739577600
  }
}
```

### ORACLE Explainability

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/oracle/explain` | No | Generate decision explanation |

#### POST /v1/oracle/explain

**Request:**
```json
{
  "decision": "approved",
  "input_data": {"credit_score": 750, "income": 5000, "debt_ratio": 0.2},
  "output_data": {"confidence": 0.92},
  "explanation_type": "feature_importance",
  "metadata": {}
}
```

**Supported explanation types:**
- `feature_importance` - Ranks input features by influence
- `counterfactual` - "What if" scenarios
- `chain_of_thought` - Step-by-step reasoning
- `rule_based` - Deterministic rule mapping
- `example_based` - Similar past cases

**Response:**
```json
{
  "decision": "approved",
  "explanation_type": "feature_importance",
  "confidence": 0.92,
  "evidence": [
    {"feature": "credit_score", "value": 750, "importance": 0.95, "description": "..."}
  ],
  "reasoning": "The decision was primarily influenced by...",
  "counterfactuals": [],
  "human_readable": "Decision: approved\nConfidence: 92.0%\n...",
  "markdown": "# Explanation\n## Decision: approved\n..."
}
```

### Agents

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/v1/agents` | Yes | List available agents |
| POST | `/api/v1/agents/execute` | Yes | Execute single agent |
| POST | `/api/v1/swarm/execute` | Yes | Execute agent swarm with consensus |

#### POST /api/v1/swarm/execute

**Request:**
```json
{
  "agent_ids": ["compliance_analyst", "risk_assessor", "decision_maker"],
  "task_type": "credit_assessment",
  "input": {"credit_score": 750},
  "consensus_strategy": "weighted"
}
```

**Consensus strategies:** `majority`, `unanimous`, `weighted`, `first`

**Response:**
```json
{
  "swarm_id": "swarm-uuid",
  "agent_ids": ["compliance_analyst", "risk_assessor", "decision_maker"],
  "status": "completed",
  "consensus_strategy": "weighted",
  "results": {
    "consensus": {"decision": "...", "confidence": 0.85, "strategy": "weighted_confidence"},
    "individual_results": [
      {"agent": "compliance_analyst", "content": "...", "confidence": 0.9}
    ]
  }
}
```

### Metrics & Testing

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/v1/metrics` | Yes | LLM provider health & circuit breaker status |
| POST | `/v1/test/cortex` | Yes | Test multi-agent consensus directly |

#### GET /v1/metrics

**Response:**
```json
{
  "status": "ok",
  "providers": {"anthropic": true, "openai": false},
  "circuit_breakers": {
    "anthropic": {"is_open": false, "failures": 0, "threshold": 5}
  },
  "agents_available": 3
}
```

### Auth & Policy

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/auth/login` | No | Get JWT token |
| POST | `/v1/auth/api-keys` | Yes | Create API key |
| GET | `/v1/policies` | Yes | List policies |
| POST | `/v1/consent` | Yes | Record consent |
| GET | `/v1/audit/logs` | Yes | Query audit logs |

## Error Responses

All errors follow a consistent format:

```json
{
  "error": {
    "correlation_id": "uuid",
    "message": "Error description",
    "status_code": 400
  }
}
```

## Rate Limiting

The API enforces a rate limit of 60 requests per minute per IP address. Exceeding this limit returns HTTP 429.
