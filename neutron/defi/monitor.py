"""PositionMonitor — lê posições do LendingProtocol via cast, avalia via RiskAssessorAgent, emite no NATS."""

from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any

from neutron.events import publish

from .models import Position, RiskEvent, RiskEventType, RiskLevel

logger = logging.getLogger("neutron.defi.monitor")

# NATS subject para eventos de risco DeFi
RISK_SUBJECT = "neotron.defi.risk.v1"

# Thresholds (basis points, espelhando LendingProtocol.sol)
WARN_THRESHOLD = 150  # health < 150 → WARNING
CRITICAL_THRESHOLD = 120  # health < 120 → CRITICAL (liquidatable)


class PositionMonitor:
    """
    Monitora posições on-chain do LendingProtocol.

    Fluxo:
      cast call → Position → RiskAssessorAgent → RiskEvent → NATS
    """

    def __init__(
        self,
        contract_address: str,
        rpc_url: str = "http://localhost:8545",
        agent: Any | None = None,  # RiskAssessorAgent (opcional — fallback heurístico)
    ):
        self.contract = contract_address
        self.rpc_url = rpc_url
        self.agent = agent

    # ── On-chain reads (via cast) ─────────────────────────────────────────────

    def _cast(self, fn_sig: str, *args: str) -> str:
        """Call a contract view function via `cast call`."""
        cmd = ["cast", "call", self.contract, fn_sig, *args, "--rpc-url", self.rpc_url]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise RuntimeError(f"cast call failed: {result.stderr.strip()}")
            return result.stdout.strip()
        except FileNotFoundError:
            raise RuntimeError("cast not found — run inside nix develop")

    def fetch_position(self, loan_id: str) -> Position:
        """Read a loan from chain and return a Position."""
        # getLoan returns tuple: (borrower, principal, collateral, ...)
        raw = self._cast(
            "getLoan(bytes32)(address,uint256,uint256,uint256,uint256,uint256,bool,bool)", loan_id
        )
        parts = [p.strip() for p in raw.strip("()").split(",")]

        borrower = parts[0]
        principal = int(parts[1])
        collateral = int(parts[2])
        accrued_interest = int(parts[4]) if len(parts) > 4 else 0
        active = parts[-1].lower() == "true"

        # getLoanHealthFactor returns basis points (10000 = 100%)
        hf_raw = self._cast("getLoanHealthFactor(bytes32)(uint256)", loan_id)
        hf_bp = int(hf_raw) if hf_raw.isdigit() else 10000
        hf = hf_bp / 100.0  # convert to percentage

        liquidatable = self._cast("isLiquidatable(bytes32)(bool)", loan_id).lower() == "true"

        return Position(
            loan_id=loan_id,
            borrower=borrower,
            collateral=collateral,
            principal=principal,
            accrued_interest=accrued_interest,
            health_factor=hf,
            liquidatable=liquidatable,
            active=active,
        )

    def fetch_pool_status(self) -> dict[str, Any]:
        """Read pool-level metrics."""
        raw = self._cast("getPoolStatus()(uint256,uint256,uint256,uint256)")
        parts = [p.strip() for p in raw.strip("()").split(",")]
        return {
            "total_deposits": int(parts[0]),
            "total_borrowed": int(parts[1]),
            "available_liquidity": int(parts[2]),
            "utilization_rate": int(parts[3]),
        }

    # ── Risk assessment ───────────────────────────────────────────────────────

    async def _assess_with_agent(self, position: Position) -> dict[str, Any]:
        """Run RiskAssessorAgent on the position. Falls back to heuristic if no agent."""
        if self.agent is None:
            return self._heuristic_assessment(position)

        try:
            from neutron.orchestration.cortex import Task

            task = Task(
                input=json.dumps(position.to_dict()),
                context={"source": "defi_monitor", "contract": self.contract},
            )
            result = await self.agent.execute(task)
            return json.loads(result.output) if isinstance(result.output, str) else result.output
        except Exception as e:
            logger.warning("RiskAssessorAgent failed (%s) — using heuristic", e)
            return self._heuristic_assessment(position)

    def _heuristic_assessment(self, position: Position) -> dict[str, Any]:
        """Deterministic fallback when no LLM agent is available."""
        hf = position.health_factor
        if hf >= 150:
            output, score = "approve", 0.1
            factors = ["health factor healthy"]
            mitigations = []
        elif hf >= 130:
            output, score = "approve", 0.3
            factors = ["health factor approaching warning threshold"]
            mitigations = ["monitor closely", "consider adding collateral"]
        elif hf >= 120:
            output, score = "escalate", 0.7
            factors = ["health factor in warning zone", f"LTV={position.ltv:.1%}"]
            mitigations = ["add collateral immediately", "partial repayment recommended"]
        else:
            output, score = "deny", 0.95
            factors = ["position liquidatable", f"health_factor={hf:.1f} < 120"]
            mitigations = ["immediate liquidation required"]
        return {
            "output": output,
            "confidence": 0.8,
            "explanation": f"Heuristic assessment: health_factor={hf:.1f}",
            "risk_score": score,
            "risk_factors": factors,
            "mitigations": mitigations,
        }

    # ── Main entry point ──────────────────────────────────────────────────────

    async def evaluate(self, loan_id: str) -> RiskEvent | None:
        """
        Fetch position, assess risk, emit NATS event if warning or critical.
        Returns the RiskEvent emitted, or None if position is healthy.
        """
        position = self.fetch_position(loan_id)

        if not position.active:
            logger.debug("loan %s inactive — skipping", loan_id)
            return None

        if position.risk_level == RiskLevel.HEALTHY:
            logger.debug("loan %s healthy (hf=%.1f)", loan_id, position.health_factor)
            return None

        assessment = await self._assess_with_agent(position)

        event_type = (
            RiskEventType.LIQUIDATION_THRESHOLD
            if position.liquidatable
            else RiskEventType.HEALTH_FACTOR_DROP
        )

        event = RiskEvent(
            event_type=event_type,
            loan_id=loan_id,
            borrower=position.borrower,
            risk_level=position.risk_level,
            health_factor=position.health_factor,
            ltv=position.ltv,
            assessment=assessment,
        )

        published = await publish(event.nats_subject(), event.to_dict())
        logger.info(
            "risk event emitted | loan=%s level=%s hf=%.1f ltv=%.1% published=%s",
            loan_id,
            position.risk_level.value,
            position.health_factor,
            position.ltv,
            published,
        )

        return event

    async def evaluate_pool(self, loan_ids: list[str]) -> list[RiskEvent]:
        """Evaluate multiple positions concurrently."""
        results = await asyncio.gather(
            *[self.evaluate(lid) for lid in loan_ids],
            return_exceptions=True,
        )
        events = []
        for lid, r in zip(loan_ids, results):
            if isinstance(r, Exception):
                logger.warning("evaluate(%s) failed: %s", lid, r)
            elif r is not None:
                events.append(r)
        return events
