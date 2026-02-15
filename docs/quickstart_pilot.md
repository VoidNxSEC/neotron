# NEXUS Quickstart Pilot Guide

Get the NEXUS compliance platform running in 30 minutes.

## Prerequisites

- Python 3.11+
- An LLM API key (at least one):
  - Anthropic: `ANTHROPIC_API_KEY`
  - OpenAI: `OPENAI_API_KEY`
  - DeepSeek: `DEEPSEEK_API_KEY`

## 1. Setup Environment

```bash
cd neutron

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

## 2. Configure API Keys

```bash
# Set at least one LLM provider
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional: set API secret for JWT auth
export API_SECRET_KEY="your-secret-key-here"
```

## 3. Verify LLM Connectivity

```bash
python demos/test_llm_integration.py
```

Expected output: providers initialized, health checks passing, agent execution working.

## 4. Start the Server

```bash
uvicorn neutron.api.server:app --host 0.0.0.0 --port 8000
```

## 5. Test Core Endpoints

### Health Check

```bash
curl http://localhost:8000/health
```

### Compliance Validation (4-Layer Flow)

```bash
curl -X POST http://localhost:8000/v1/compliance/validate \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "test_customer",
    "action": "loan_approval",
    "data": {"credit_score": 750, "amount": 10000},
    "consent_token": "lgpd_consent_test",
    "regulation": "LGPD"
  }'
```

### ORACLE Explainability

```bash
curl -X POST http://localhost:8000/v1/oracle/explain \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "approved",
    "input_data": {"credit_score": 750, "income": 5000},
    "output_data": {"confidence": 0.92},
    "explanation_type": "feature_importance"
  }'
```

### Agent Swarm Execution

```bash
curl -X POST http://localhost:8000/api/v1/swarm/execute \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "agent_ids": ["compliance_analyst", "risk_assessor", "decision_maker"],
    "task_type": "credit_assessment",
    "input": {"credit_score": 750, "amount": 10000},
    "consensus_strategy": "weighted"
  }'
```

### LLM Metrics

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/v1/metrics
```

## 6. Run the EU AI Act Demo

```bash
python demos/eu_ai_act_demo.py
```

This demonstrates a full credit scoring scenario with all 4 layers and EU AI Act Article mapping.

## 7. Run Tests

```bash
# All tests
python -m pytest tests/ -v

# Compliance tests only
python -m pytest tests/compliance/ -v

# Skip kernel-level tests (CI)
CI=true python -m pytest tests/compliance/ -v
```

## Architecture Overview

```
Request --> SENTINEL (consent validation)
        --> BASTION (kernel enforcement)
        --> CORTEX (multi-agent LLM consensus)
            + ORACLE (explainability)
        --> AUDIT (immutable IPFS/Arweave log)
        --> Response
```

## Troubleshooting

**No LLM providers available**: Set at least one API key environment variable.

**Temporal connection error on startup**: Expected if Temporal is not running. The API still starts but task endpoints return 503.

**BASTION tests skipped**: Normal in CI or non-Linux environments. Kernel-level enforcement requires Linux with seccomp-BPF support.
