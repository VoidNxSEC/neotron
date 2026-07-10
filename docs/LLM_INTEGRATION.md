# LLM Integration Guide

**Last Updated**: 2026-02-15

## Overview

NEXUS CORTEX agents now support **real LLM integration** with automatic fallback chain, retry logic, and circuit breakers. This enables production-ready multi-agent orchestration with enterprise-grade resilience.

## Supported Providers

| Provider | API | Status | Speed | Cost | Best For |
|----------|-----|--------|-------|------|----------|
| **Anthropic Claude** | `claude-3-5-sonnet-20241022` | ✅ Primary | Fast | $$$ | Complex reasoning, compliance |
| **DeepSeek** | `deepseek-chat` | ✅ Fallback | Very Fast | $ | Cost-effective, high throughput |
| **OpenAI GPT** | `gpt-4`, `gpt-3.5-turbo` | ✅ Fallback | Fast | $$ | General purpose |
| **llama.cpp** | Local models | ✅ Fallback | Depends | Free | Privacy, offline operation |

## Quick Start

### 1. Install Dependencies

```bash
# From neutron directory
cd /path/to/neutron

# Install LLM provider packages
pip install anthropic openai

# Or use pip-tools/uv
pip install -e .
```

### 2. Configure API Keys

Create a `.env` file (or copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```bash
# Primary provider (Claude)
ANTHROPIC_API_KEY=sk-ant-api03-...

# Fallback providers
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...

# Primary provider selection
LLM_PRIMARY_PROVIDER=anthropic

# Fallback chain (tries in order)
LLM_FALLBACK_CHAIN=deepseek,openai,llamacpp
```

### 3. Test Integration

```bash
# Run integration tests
PYTHONPATH=. python demos/test_llm_integration.py

# Or run quick health check
python -c "
import asyncio
from neutron.agents.llm_client import LLMClient

async def test():
    client = LLMClient()
    health = await client.health_check()
    print('Provider Health:', health)

asyncio.run(test())
"
```

## Architecture

### Fallback Chain

The LLM client automatically falls back to alternative providers if the primary fails:

```
Request → Anthropic (primary)
           ↓ (fails)
         DeepSeek (fallback 1)
           ↓ (fails)
         OpenAI (fallback 2)
           ↓ (fails)
         llama.cpp (fallback 3)
           ↓ (fails)
         Error: All providers failed
```

### Retry Logic

Each provider is retried with exponential backoff:

```
Attempt 1 → fail → wait 1s
Attempt 2 → fail → wait 2s
Attempt 3 → fail → try next provider
```

Configuration:
```bash
ANTHROPIC_MAX_RETRIES=3
ANTHROPIC_RETRY_DELAY=1.0  # Initial delay in seconds
```

### Circuit Breakers

Providers that repeatedly fail are temporarily disabled:

```
Failures: 0/5 → CLOSED (normal operation)
Failures: 3/5 → CLOSED (still trying)
Failures: 5/5 → OPEN (stop trying for 60s)
After 60s  → HALF-OPEN (try once)
Success    → CLOSED (back to normal)
```

Configuration:
```bash
ANTHROPIC_CIRCUIT_BREAKER_THRESHOLD=5  # Failures before opening
ANTHROPIC_CIRCUIT_BREAKER_TIMEOUT=60.0  # Seconds before retry
```

## Usage

### Basic Text Generation

```python
from neutron.agents.llm_client import LLMClient

client = LLMClient()

# Simple generation
response = await client.generate(
    prompt="What is the capital of France?",
    max_tokens=50,
)

print(response.content)  # "The capital of France is Paris."
print(response.total_tokens)  # 15
print(response.model)  # "claude-3-5-sonnet-20241022"
```

### Chat Completion

```python
messages = [
    {"role": "system", "content": "You are a helpful AI assistant."},
    {"role": "user", "content": "What is 2+2?"},
]

response = await client.generate_chat(
    messages=messages,
    temperature=0.3,
    max_tokens=100,
)
```

### Provider Hints

```python
from neutron.core.config import ProviderType

# Prefer DeepSeek for cost savings
response = await client.generate(
    prompt="Quick question",
    provider_hint=ProviderType.DEEPSEEK,
)
```

### CORTEX Agents

```python
from neutron.agents.cortex import Agent

agent = Agent(
    name="compliance_analyst",
    role="LGPD compliance expert",
    system_prompt="You are an LGPD compliance expert. Analyze data processing activities for compliance.",
)

task = {
    "type": "compliance_check",
    "description": "Check if this data processing requires consent",
    "data": {
        "action": "email_marketing",
        "data_types": ["email", "name"],
        "purpose": "promotional offers",
    },
}

result = await agent.execute(task)

print(f"Decision: {result.content}")
print(f"Confidence: {result.confidence}")
print(f"Tokens used: {result.metadata['tokens']}")
```

### Multi-Agent Swarm

```python
from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy

# Create specialized agents
analyst = Agent(name="analyst", role="risk_analyst")
auditor = Agent(name="auditor", role="compliance_auditor")
decision_maker = Agent(name="decision", role="decision_maker")

# Create swarm
swarm = AgentSwarm(
    agents=[analyst, auditor, decision_maker],
    consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
)

# Execute task with consensus
result = await swarm.broadcast_task(task)

print(f"Consensus: {result['consensus']['decision']}")
print(f"Confidence: {result['consensus']['confidence']}")

for r in result["individual_results"]:
    print(f"  {r['agent']}: {r['content']} (confidence: {r['confidence']})")
```

## Health Monitoring

### Check Provider Status

```python
client = LLMClient()

# Health check (calls each provider)
health = await client.health_check()
# {'anthropic': True, 'deepseek': True, 'openai': False, 'llamacpp': False}

# Circuit breaker status
status = client.get_circuit_breaker_status()
# {
#   'anthropic': {'is_open': False, 'failures': 0, 'threshold': 5},
#   'deepseek': {'is_open': False, 'failures': 0, 'threshold': 5},
#   ...
# }
```

### Prometheus Metrics (TODO)

Future integration with `neutron.metrics` module:

```
llm_requests_total{provider="anthropic", status="success"} 1234
llm_requests_total{provider="anthropic", status="failure"} 5
llm_request_duration_seconds{provider="anthropic"} 0.523
llm_tokens_total{provider="anthropic", type="prompt"} 45000
llm_tokens_total{provider="anthropic", type="completion"} 12000
llm_circuit_breaker_state{provider="anthropic"} 0  # 0=closed, 1=open
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PRIMARY_PROVIDER` | `anthropic` | Primary LLM provider |
| `LLM_FALLBACK_CHAIN` | `deepseek,openai,llamacpp` | Fallback order |
| `LLM_ENABLE_RETRIES` | `true` | Enable exponential backoff retries |
| `LLM_ENABLE_CIRCUIT_BREAKER` | `true` | Enable circuit breakers |
| `LLM_LOG_REQUESTS` | `true` | Log all LLM requests |
| `{PROVIDER}_API_KEY` | - | API key for provider |
| `{PROVIDER}_MODEL` | (varies) | Model name |
| `{PROVIDER}_TEMPERATURE` | `0.3` | Temperature (0.0-1.0) |
| `{PROVIDER}_MAX_TOKENS` | `1024` | Max tokens per request |
| `{PROVIDER}_TIMEOUT` | `30.0` | Request timeout (seconds) |
| `{PROVIDER}_MAX_RETRIES` | `3` | Retry attempts |

Replace `{PROVIDER}` with: `ANTHROPIC`, `OPENAI`, `DEEPSEEK`, `LLAMACPP`

### Programmatic Configuration

```python
from neutron.core.config import LLMConfig, ProviderType, ProviderConfig

# Custom configuration
config = LLMConfig(
    primary_provider=ProviderType.DEEPSEEK,
    fallback_chain=[ProviderType.OPENAI, ProviderType.ANTHROPIC],
    enable_retries=True,
    enable_circuit_breaker=True,
)

# Configure specific provider
config.providers[ProviderType.DEEPSEEK] = ProviderConfig(
    provider_type=ProviderType.DEEPSEEK,
    api_key="sk-...",
    model="deepseek-chat",
    temperature=0.2,
    max_tokens=2048,
    circuit_breaker_threshold=10,
)

# Use custom config
client = LLMClient(config=config)
```

## Troubleshooting

### No providers are healthy

```
⚠️  WARNING: No providers are healthy!
```

**Solution**: Verify API keys are set correctly:

```bash
# Check environment variables
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Test API key manually
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":10,"messages":[{"role":"user","content":"ping"}]}'
```

### ImportError: anthropic package required

```
ImportError: anthropic package required for AnthropicProvider
```

**Solution**: Install missing package:

```bash
pip install anthropic  # For Anthropic/Claude
pip install openai     # For OpenAI and DeepSeek
```

### Circuit breaker is open

```
RuntimeError: anthropic circuit breaker is open, skipping
```

**Cause**: Provider failed 5+ times recently (default threshold)

**Solution**:
1. Wait 60s for circuit breaker to reset
2. Check provider API status
3. Verify API key is valid
4. Increase threshold: `ANTHROPIC_CIRCUIT_BREAKER_THRESHOLD=10`

### All LLM providers failed

```
RuntimeError: All LLM providers failed. Last error: ...
```

**Solution**:
1. Check network connectivity
2. Verify API keys for all providers
3. Check provider API status pages
4. Ensure at least one provider is configured and healthy

## Cost Optimization

### Strategy 1: DeepSeek Primary

DeepSeek is ~10x cheaper than Claude/GPT-4:

```bash
LLM_PRIMARY_PROVIDER=deepseek
LLM_FALLBACK_CHAIN=anthropic,openai
```

**Best for**: High-volume, less critical tasks

### Strategy 2: Hybrid Approach

Use DeepSeek for fast tasks, Claude for complex reasoning:

```python
# Fast task - use DeepSeek
response = await client.generate(
    prompt="Quick factual question",
    provider_hint=ProviderType.DEEPSEEK,
)

# Complex task - use Claude
response = await client.generate(
    prompt="Analyze LGPD compliance implications...",
    provider_hint=ProviderType.ANTHROPIC,
)
```

### Strategy 3: Local Fallback

Use llama.cpp for offline/free tier:

```bash
# Run llama.cpp server
llama-server --model qwen-2.5-7b.gguf --port 8081

# Configure
LLAMACPP_ENABLED=true
LLM_FALLBACK_CHAIN=deepseek,openai,llamacpp
```

## Next Steps

- [ ] **Task #2**: Integrate with 4-layer compliance flow (SENTINEL → BASTION → CORTEX)
- [ ] **Task #5**: Connect pgvector memory store for agent learning
- [ ] **Task #6**: Create EU AI Act demo using real LLM agents
- [ ] Add Prometheus metrics for token usage tracking
- [ ] Implement token budget enforcement
- [ ] Add streaming support for real-time responses

## See Also

- [CORTEX Architecture](./architecture/CORTEX.md)
- [Agent Development Guide](./AGENT_DEVELOPMENT.md)
- [API Reference](./API.md)
