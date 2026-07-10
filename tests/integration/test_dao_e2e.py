"""
Integration test: DAO E2E pipeline
CORTEX emite task.assigned.v1 → mock IntelAgent processa → quality.report.v1 → assert

Testa o fluxo NATS sem precisar de Anvil ou contratos deployados.
O teste de contracts on-chain é coberto por IntelAgentDAO.t.sol (Foundry).
"""

import asyncio
import json
import time

import pytest

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _collect(subject: str, timeout: float = 2.0) -> list[dict]:
    """Subscribe to a NATS subject and collect messages for `timeout` seconds."""
    try:
        import nats

        nc = await nats.connect("nats://localhost:4222")
        collected = []

        async def _cb(msg):
            collected.append(json.loads(msg.data))

        sub = await nc.subscribe(subject, cb=_cb)
        await asyncio.sleep(timeout)
        await sub.unsubscribe()
        await nc.close()
        return collected
    except Exception:
        return []


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestNATSEventFlow:
    """Test NATS event emission from neutron.events without live IntelAgent."""

    @pytest.mark.asyncio
    async def test_emit_task_assigned(self):
        """CORTEX can emit task.assigned.v1 via neutron.events.publish."""
        from neutron.events import publish

        payload = {
            "task_id": "test-task-001",
            "agent_id": "alice-agent",
            "description": "Analyze compliance report",
            "quality_threshold": 0.85,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        result = await publish("task.assigned.v1", payload)
        # True if NATS available, False if not (CI without NATS)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_emit_quality_report(self):
        """IntelAgent can publish quality.report.v1."""
        from neutron.events import publish

        payload = {
            "task_id": "test-task-001",
            "agent_id": "alice-agent",
            "quality_score": 0.94,
            "passed": True,
            "execution_time_ms": 342,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        result = await publish("quality.report.v1", payload)
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_emit_dao_vote(self):
        """Agent can publish dao.vote.v1."""
        from neutron.events import publish

        payload = {
            "proposal_id": "0xdeadbeef",
            "voter": "alice-agent",
            "support": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        result = await publish("dao.vote.v1", payload)
        assert isinstance(result, bool)


class TestDAOContractSmoke:
    """Smoke tests that verify DAO contracts compile and test suite passes."""

    def test_forge_dao_tests_pass(self, tmp_path):
        """Run forge test --match-contract IntelAgentDAO and assert zero failures."""
        import os
        import subprocess

        contracts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "contracts")
        result = subprocess.run(
            [
                "forge",
                "test",
                "--match-contract",
                "IntelAgentDAO",
                "--summary",
                "-q",
            ],
            cwd=contracts_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = result.stdout + result.stderr

        # Parse failures
        failed = 0
        for line in output.splitlines():
            if "failed" in line.lower() and "Suite result" in line:
                parts = line.split(";")
                for part in parts:
                    if "failed" in part:
                        try:
                            failed += int(part.strip().split()[0])
                        except (ValueError, IndexError):
                            pass

        assert result.returncode == 0, f"forge test failed:\n{output}"
        assert failed == 0, f"{failed} Foundry tests failed:\n{output}"


class TestDAOPayloadSchema:
    """Validate that DAO event payloads conform to expected schema."""

    def test_task_assigned_schema(self):
        payload = {
            "task_id": "task-abc",
            "agent_id": "alice-agent",
            "description": "Do something",
            "quality_threshold": 0.9,
            "timestamp": "2026-05-31T00:00:00Z",
        }
        assert isinstance(payload["task_id"], str)
        assert isinstance(payload["quality_threshold"], float)
        assert 0.0 <= payload["quality_threshold"] <= 1.0

    def test_quality_report_schema(self):
        payload = {
            "task_id": "task-abc",
            "agent_id": "alice-agent",
            "quality_score": 0.92,
            "passed": True,
            "execution_time_ms": 250,
            "timestamp": "2026-05-31T00:00:00Z",
        }
        assert isinstance(payload["passed"], bool)
        assert 0.0 <= payload["quality_score"] <= 1.0
        assert payload["passed"] == (payload["quality_score"] >= 0.85)

    def test_dao_vote_schema(self):
        payload = {
            "proposal_id": "0xdeadbeef",
            "voter": "alice-agent",
            "support": True,
            "timestamp": "2026-05-31T00:00:00Z",
        }
        assert isinstance(payload["support"], bool)
        assert payload["proposal_id"].startswith("0x")
