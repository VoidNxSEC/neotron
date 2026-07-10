"""
Temporal workflow para monitoramento de risco DeFi por posição.

Fluxo:
  fetch_position_activity  →  assess_risk_activity  →  emit_risk_event_activity
  ↑_______________________↑  (loop com intervalo configurável)
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

from neutron.defi.models import RiskLevel

logger = logging.getLogger("neutron.orchestration.defi_workflow")

# ── Activities ────────────────────────────────────────────────────────────────


@activity.defn
async def fetch_position_activity(
    loan_id: str,
    contract_address: str,
    rpc_url: str = "http://localhost:8545",
) -> dict[str, Any]:
    """Read position from chain via PositionMonitor."""
    from neutron.defi.monitor import PositionMonitor

    monitor = PositionMonitor(contract_address, rpc_url)
    position = monitor.fetch_position(loan_id)
    return position.to_dict()


@activity.defn
async def assess_risk_activity(position_dict: dict[str, Any]) -> dict[str, Any]:
    """Run heuristic risk assessment on a position dict (no LLM required)."""
    from neutron.defi.models import Position
    from neutron.defi.monitor import PositionMonitor

    position = Position(
        loan_id=position_dict["loan_id"],
        borrower=position_dict["borrower"],
        collateral=position_dict["collateral_wei"],
        principal=position_dict["debt_wei"],
        accrued_interest=0,
        health_factor=position_dict["health_factor"],
        liquidatable=position_dict["liquidatable"],
        active=True,
    )
    monitor = PositionMonitor("", "")  # no chain call needed
    assessment = monitor._heuristic_assessment(position)
    return {
        "position": position_dict,
        "assessment": assessment,
        "risk_level": position.risk_level.value,
        "should_alert": position.risk_level != RiskLevel.HEALTHY,
    }


@activity.defn
async def emit_risk_event_activity(assessment_result: dict[str, Any]) -> bool:
    """Emit risk event to NATS if position is not healthy."""
    if not assessment_result.get("should_alert"):
        return False

    from neutron.defi.models import RiskEvent, RiskEventType
    from neutron.events import publish

    pos = assessment_result["position"]
    event = RiskEvent(
        event_type=(
            RiskEventType.LIQUIDATION_THRESHOLD
            if pos.get("liquidatable")
            else RiskEventType.HEALTH_FACTOR_DROP
        ),
        loan_id=pos["loan_id"],
        borrower=pos["borrower"],
        risk_level=RiskLevel(assessment_result["risk_level"]),
        health_factor=pos["health_factor"],
        ltv=pos["ltv"],
        assessment=assessment_result["assessment"],
    )
    return await publish(event.nats_subject(), event.to_dict())


# ── Workflow ──────────────────────────────────────────────────────────────────


@workflow.defn
class PositionRiskWorkflow:
    """
    Monitora uma posição DeFi continuamente.
    Roda fetch → assess → emit a cada `interval_seconds` até a posição fechar.

    Uso:
        await client.start_workflow(
            PositionRiskWorkflow.run,
            args=["0x<loan_id>", "0x<contract>"],
            id=f"risk-{loan_id}",
            task_queue="defi-risk",
        )
    """

    @workflow.run
    async def run(
        self,
        loan_id: str,
        contract_address: str,
        rpc_url: str = "http://localhost:8545",
        interval_seconds: int = 30,
        max_iterations: int = 0,  # 0 = rodar indefinidamente
    ) -> dict[str, Any]:
        retry = RetryPolicy(maximum_attempts=3, backoff_coefficient=2.0)
        iterations = 0
        last_event: dict[str, Any] | None = None

        while True:
            # 1. Busca posição on-chain
            position_dict = await workflow.execute_activity(
                fetch_position_activity,
                args=[loan_id, contract_address, rpc_url],
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=retry,
            )

            # Posição inativa → encerra o workflow
            if not position_dict.get("active", True):
                workflow.logger.info("loan %s closed — workflow complete", loan_id)
                break

            # 2. Avalia risco
            assessment_result = await workflow.execute_activity(
                assess_risk_activity,
                args=[position_dict],
                start_to_close_timeout=timedelta(seconds=15),
                retry_policy=retry,
            )

            # 3. Emite evento NATS se necessário
            if assessment_result["should_alert"]:
                await workflow.execute_activity(
                    emit_risk_event_activity,
                    args=[assessment_result],
                    start_to_close_timeout=timedelta(seconds=15),
                    retry_policy=retry,
                )
                last_event = assessment_result

            iterations += 1
            if max_iterations > 0 and iterations >= max_iterations:
                break

            await workflow.sleep(interval_seconds)

        return {
            "loan_id": loan_id,
            "iterations": iterations,
            "last_event": last_event,
        }
