# Agentic Core - Phase 1 MVP

**Quick Prototype**: DSPy + Ensemble Reasoning Validation

## Overview

This is a proof-of-concept implementation of advanced agentic AI pipelines with:
- **DSPy integration** for prompt optimization
- **Multi-provider ensemble** for improved accuracy
- **Voting strategies** (majority, confidence-weighted, best-of-n, unanimous)
- **Async execution** for parallel provider calls

## Architecture

```
┌─────────────────────────────────────────┐
│         DSPy Adapter Layer              │
│  Connects DSPy to LLM providers         │
└────────────────┬────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│      Ensemble Reasoning Engine          │
│  • Parallel execution                   │
│  • Voting strategies                    │
│  • Error handling                       │
└────────────────┬────────────────────────┘
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
  ┌──────────┐      ┌──────────┐
  │ DeepSeek │      │  Local   │
  │   API    │      │  Ollama  │
  └──────────┘      └──────────┘
```

## Setup

### 1. Install Dependencies

```bash
cd /home/kernelcore/dev/low-level/agentic-core
pip install -r requirements.txt
```

### 2. Configure API Keys

**DeepSeek** (recommended for testing):
```bash
export DEEPSEEK_API_KEY="your-api-key-here"
```

**OpenAI** (optional):
```bash
export OPENAI_API_KEY="your-api-key-here"
```

**Local llama.cpp** (optional):
```bash
# Make sure llama.cpp server is running
# Example: ./llama-server -m /path/to/model.gguf --port 8080
# Default port: 8080
# API: http://localhost:8080/v1 (OpenAI-compatible)
```

### 3. Test Installation

```bash
python -c "import dspy; print('DSPy installed successfully')"
```

## Usage

### Quick Start - Demo Script

```bash
cd /home/kernelcore/dev/low-level/agentic-core
python examples/simple_ensemble.py
```

This runs 5 comprehensive tests:
1. Simple factual question
2. Reasoning question with multiple strategies
3. Multi-provider ensemble
4. Disagreement handling
5. Aggregate statistics

### Programmatic Usage

```python
import asyncio
from ensemble_reasoning import EnsembleReasoner

async def main():
    # Create ensemble with provider list
    ensemble = EnsembleReasoner(["deepseek", "local"])

    # Execute with majority voting
    result = await ensemble.reason(
        task="What is the capital of France?",
        strategy="majority",
        temperature=0.3
    )

    print(f"Answer: {result.answer}")
    print(f"Confidence: {result.confidence:.2%}")
    print(f"Votes: {result.provider_votes}")

asyncio.run(main())
```

### Voting Strategies

**1. Majority Vote** (simple, robust):
```python
result = await ensemble.reason(task="...", strategy="majority")
```

**2. Confidence-Weighted** (smart aggregation):
```python
result = await ensemble.reason(task="...", strategy="confidence_weighted")
```

**3. Best-of-N** (highest confidence):
```python
result = await ensemble.reason(task="...", strategy="best_of_n")
```

**4. Unanimous** (strict consensus):
```python
result = await ensemble.reason(task="...", strategy="unanimous")
```

## File Structure

```
agentic-core/
├── __init__.py              Package initialization
├── dspy_adapter.py          DSPy ↔ Provider integration
├── ensemble_reasoning.py    Multi-model voting logic
├── requirements.txt         Dependencies
├── README.md               This file
├── examples/
│   └── simple_ensemble.py  Demo script
└── workflows/              (Future: Temporal workflows)
```

## Validation Goals

### ✅ Phase 1 MVP Success Criteria

1. **Integration works**: DSPy adapters connect to providers
2. **Ensemble voting**: Multiple strategies produce consistent results
3. **Error handling**: Gracefully handles provider failures
4. **Performance**: Parallel execution reduces latency
5. **Accuracy**: Ensemble improves over single model

### 📊 Metrics to Track

```python
# Get statistics
stats = ensemble.get_stats()

print(f"Average Confidence: {stats['average_confidence']:.2%}")
print(f"Average Latency: {stats['average_latency_ms']:.0f}ms")
print(f"Provider Success Rates: {stats['provider_success_rates']}")
```

## Expected Results

### Test 1: Simple Factual Question
- **Question**: "What is the capital of France?"
- **Expected**: High confidence (>90%), unanimous "Paris"
- **Validates**: Basic provider integration

### Test 2: Reasoning Question
- **Question**: "If a train travels 120 km in 2 hours, what is its average speed?"
- **Expected**: Correct calculation (60 km/h)
- **Validates**: Reasoning capability, strategy comparison

### Test 3: Multi-Provider
- **Scenario**: Multiple providers vote
- **Expected**: Majority consensus, confidence metrics
- **Validates**: Ensemble aggregation logic

### Test 4: Disagreement
- **Question**: Subjective/ambiguous question
- **Expected**: Graceful handling, confidence-weighted selection
- **Validates**: Conflict resolution

## Troubleshooting

### "ModuleNotFoundError: No module named 'dspy'"
```bash
pip install dspy-ai
```

### "All providers failed"
Check:
1. API key is set: `echo $DEEPSEEK_API_KEY`
2. API key is valid (test with curl)
3. Network connectivity

### "Timeout after 30s"
- Increase timeout: `await ensemble.reason(..., timeout=60)`
- Check provider status
- Try with different provider

### Local llama.cpp not responding
```bash
# Check if server is running
ps aux | grep llama-server

# Test API endpoint
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [{"role": "user", "content": "Hello"}]
  }'

# Start llama.cpp server if not running:
# ./llama-server -m /path/to/your/model.gguf --port 8080
```

## Next Steps (After Validation)

1. **Add semantic caching** (ChromaDB) for cost reduction
2. **Integrate MLflow** for observability
3. **Add Temporal workflows** for orchestration
4. **Implement cognitive patterns** (CoT, ToT, Reflexion)
5. **Build CORTEX engine** (self-optimizing system)

## Performance Benchmarks

### Expected (Single Provider)
- Latency: 500-2000ms
- Tokens: 50-200 per response
- Cost: $0.0001-$0.001 per query (DeepSeek)

### Expected (3-Provider Ensemble)
- Latency: 600-2500ms (parallel)
- Tokens: 150-600 total
- Cost: $0.0003-$0.003 per query
- **Accuracy improvement**: +5-15% (estimated)

## API Reference

### DSPyProviderAdapter

```python
adapter = DSPyProviderAdapter(provider_name="deepseek", api_key="...")
response = adapter.basic_request(prompt="...", temperature=0.7, max_tokens=512)
```

### EnsembleReasoner

```python
ensemble = EnsembleReasoner(providers=["deepseek", "openai", "local"])

result = await ensemble.reason(
    task="question here",
    strategy="majority",  # or confidence_weighted, best_of_n, unanimous
    temperature=0.7,
    max_tokens=512,
    timeout=30
)

# Result fields:
result.answer              # Final aggregated answer
result.confidence          # 0.0-1.0 confidence score
result.provider_votes      # Dict[provider -> vote]
result.reasoning           # Explanation of voting
result.individual_responses  # List[ProviderResponse]
result.total_latency_ms    # Total time
result.total_tokens_used   # Approximate token count
```

## Contributing

This is Phase 1 MVP. Focus areas:
- Test with different providers
- Measure accuracy on benchmark datasets
- Report bugs/issues
- Suggest voting strategy improvements

## License

Part of the Agentic AI Pipeline project.
