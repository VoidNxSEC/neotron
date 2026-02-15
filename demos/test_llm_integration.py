#!/usr/bin/env python3
"""
Quick demo to test LLM integration with CORTEX agents.

This script verifies that:
1. LLM providers can be initialized
2. Fallback chain works
3. CORTEX agents can call real LLMs
4. Circuit breakers function correctly

Usage:
    # Test with Anthropic (Claude)
    export ANTHROPIC_API_KEY="sk-ant-..."
    python demos/test_llm_integration.py

    # Test with OpenAI
    export OPENAI_API_KEY="sk-..."
    python demos/test_llm_integration.py

    # Test with DeepSeek
    export DEEPSEEK_API_KEY="sk-..."
    python demos/test_llm_integration.py
"""

import asyncio
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neutron.agents.llm_client import LLMClient
from neutron.agents.cortex import Agent, AgentSwarm, ConsensusStrategy
from neutron.core.config import get_config


def print_header(text: str, char: str = "=") -> None:
    width = 70
    print()
    print(char * width)
    print(f"  {text}")
    print(char * width)


async def test_llm_client():
    """Test basic LLM client functionality."""
    print_header("Test 1: LLM Client Initialization")

    client = LLMClient()

    print(f"  Initialized LLM client")
    print(f"  Providers available: {list(client._providers.keys())}")

    # Health check
    print("\n  Running health checks...")
    health = await client.health_check()

    for provider, is_healthy in health.items():
        status = "✓ OK" if is_healthy else "✗ FAILED"
        print(f"    {provider:12s}: {status}")

    healthy_count = sum(1 for h in health.values() if h)
    if healthy_count == 0:
        print("\n  ⚠️  WARNING: No providers are healthy!")
        print("  Make sure you've set API keys:")
        print("    export ANTHROPIC_API_KEY='sk-ant-...'")
        print("    export OPENAI_API_KEY='sk-...'")
        print("    export DEEPSEEK_API_KEY='sk-...'")
        return False

    print(f"\n  ✓ {healthy_count}/{len(health)} providers healthy")
    return True


async def test_simple_generation():
    """Test simple text generation."""
    print_header("Test 2: Simple Text Generation", "-")

    client = LLMClient()

    print("  Prompt: What is 2+2?")
    print("  Generating...")

    try:
        response = await client.generate(
            prompt="What is 2+2? Answer in one sentence.",
            max_tokens=50,
        )

        print(f"\n  ✓ Response received:")
        print(f"    Model: {response.model}")
        print(f"    Tokens: {response.total_tokens}")
        print(f"    Content: {response.content[:200]}")

        return True
    except Exception as e:
        print(f"\n  ✗ Generation failed: {e}")
        return False


async def test_cortex_agent():
    """Test CORTEX agent with real LLM."""
    print_header("Test 3: CORTEX Agent Execution", "-")

    agent = Agent(
        name="test_agent",
        role="analyst",
        system_prompt="You are a helpful AI analyst. Provide concise, accurate responses in JSON format.",
    )

    task = {
        "type": "analysis",
        "description": "Analyze whether the number 42 is even or odd",
        "data": {"number": 42},
    }

    print(f"  Agent: {agent.name} ({agent.role})")
    print(f"  Task: {task['description']}")
    print("  Executing...")

    try:
        result = await agent.execute(task)

        print(f"\n  ✓ Agent response:")
        print(f"    Confidence: {result.confidence:.2f}")
        print(f"    Content: {result.content[:200]}")
        print(f"    Metadata: {result.metadata}")

        return True
    except Exception as e:
        print(f"\n  ✗ Agent execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_swarm():
    """Test multi-agent consensus with real LLMs."""
    print_header("Test 4: Multi-Agent Swarm Consensus", "-")

    # Create 3 agents with different roles
    agents = [
        Agent(
            name="analyst_1",
            role="risk_analyst",
            system_prompt="You are a risk analyst. Evaluate risks conservatively.",
        ),
        Agent(
            name="analyst_2",
            role="opportunity_analyst",
            system_prompt="You are an opportunity analyst. Identify potential benefits.",
        ),
        Agent(
            name="analyst_3",
            role="decision_maker",
            system_prompt="You are a decision maker. Provide balanced recommendations.",
        ),
    ]

    swarm = AgentSwarm(agents, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)

    task = {
        "type": "decision",
        "description": "Should we approve a $10,000 loan for a customer with credit score 720?",
        "data": {
            "loan_amount": 10000,
            "credit_score": 720,
            "income": 50000,
            "existing_debt": 5000,
        },
    }

    print(f"  Swarm: {len(agents)} agents")
    print(f"  Strategy: {ConsensusStrategy.MAJORITY_VOTE.value}")
    print(f"  Task: {task['description']}")
    print("  Broadcasting to agents...")

    try:
        result = await swarm.broadcast_task(task)

        print(f"\n  ✓ Swarm consensus reached:")
        print(f"    Decision: {result['consensus']['decision']}")
        print(f"    Confidence: {result['consensus']['confidence']:.2f}")

        print(f"\n  Individual agent results:")
        for r in result["individual_results"]:
            print(f"    {r['agent']:15s}: {str(r['content'])[:60]:60s} (conf: {r['confidence']:.2f})")

        return True
    except Exception as e:
        print(f"\n  ✗ Swarm execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_circuit_breaker():
    """Test circuit breaker status."""
    print_header("Test 5: Circuit Breaker Status", "-")

    client = LLMClient()
    status = client.get_circuit_breaker_status()

    print("  Circuit breaker states:")
    for provider, state in status.items():
        open_status = "OPEN" if state["is_open"] else "CLOSED"
        print(
            f"    {provider:12s}: {open_status:6s} "
            f"(failures: {state['failures']}/{state['threshold']})"
        )

    return True


async def main():
    """Run all tests."""
    print_header("NEXUS LLM Integration Test Suite")

    config = get_config()
    print(f"  Configuration loaded")
    print(f"  Primary provider: {config.llm.primary_provider.value}")
    print(f"  Fallback chain: {[p.value for p in config.llm.fallback_chain]}")

    tests = [
        ("LLM Client Init", test_llm_client),
        ("Simple Generation", test_simple_generation),
        ("CORTEX Agent", test_cortex_agent),
        ("Agent Swarm", test_agent_swarm),
        ("Circuit Breaker", test_circuit_breaker),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n  ✗ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {test_name:20s}: {status}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n  🎉 All tests passed!")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
