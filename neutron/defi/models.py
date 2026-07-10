"""DeFi position and risk event types — mirrors LendingProtocol.sol structs."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    HEALTHY = "healthy"  # health_factor >= 150
    WARNING = "warning"  # 120 <= health_factor < 150
    CRITICAL = "critical"  # health_factor < 120 — liquidatable


@dataclass
class Position:
    """On-chain loan position from LendingProtocol.getLoan()."""

    loan_id: str
    borrower: str
    collateral: int  # wei
    principal: int  # wei
    accrued_interest: int  # wei
    health_factor: float  # basis points / 100  (10000 bp = 100%)
    liquidatable: bool
    active: bool

    @property
    def debt(self) -> int:
        return self.principal + self.accrued_interest

    @property
    def ltv(self) -> float:
        """Loan-to-value ratio (0.0–1.0)."""
        if self.collateral == 0:
            return float("inf")
        return self.debt / self.collateral

    @property
    def risk_level(self) -> RiskLevel:
        if self.health_factor > 150:
            return RiskLevel.HEALTHY
        if self.health_factor > 120:
            return RiskLevel.WARNING
        return RiskLevel.CRITICAL  # <= 120 = liquidation threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "loan_id": self.loan_id,
            "borrower": self.borrower,
            "collateral_wei": self.collateral,
            "debt_wei": self.debt,
            "health_factor": self.health_factor,
            "ltv": round(self.ltv, 4),
            "liquidatable": self.liquidatable,
            "risk_level": self.risk_level.value,
        }


class RiskEventType(Enum):
    HEALTH_FACTOR_DROP = "health_factor_drop"
    LIQUIDATION_THRESHOLD = "liquidation_threshold"
    LTV_SPIKE = "ltv_spike"
    COLLATERAL_CONCENTRATION = "collateral_concentration"
    POOL_UTILIZATION_HIGH = "pool_utilization_high"


@dataclass
class RiskEvent:
    """Risk event emitted to NATS subject neotron.defi.risk.v1."""

    event_type: RiskEventType
    loan_id: str
    borrower: str
    risk_level: RiskLevel
    health_factor: float
    ltv: float
    assessment: dict[str, Any] = field(default_factory=dict)  # RiskAssessorAgent output
    timestamp: str = ""

    def nats_subject(self) -> str:
        return "neotron.defi.risk.v1"

    def to_dict(self) -> dict[str, Any]:
        import time

        return {
            "event_type": self.event_type.value,
            "loan_id": self.loan_id,
            "borrower": self.borrower,
            "risk_level": self.risk_level.value,
            "health_factor": self.health_factor,
            "ltv": self.ltv,
            "assessment": self.assessment,
            "timestamp": self.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
