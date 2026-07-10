"""Unit tests para neutron/defi/ — sem chain, sem LLM."""

from neutron.defi.models import Position, RiskEvent, RiskEventType, RiskLevel


def _position(health_factor: float, liquidatable: bool = False) -> Position:
    collateral = 15_000
    debt = int(collateral / (health_factor / 100)) if health_factor > 0 else 1
    return Position(
        loan_id="0xabc",
        borrower="0xdeadbeef",
        collateral=collateral,
        principal=debt,
        accrued_interest=0,
        health_factor=health_factor,
        liquidatable=liquidatable,
        active=True,
    )


# ── Risk level classification ──────────────────────────────────────────────


def test_healthy():
    p = _position(200.0)
    assert p.risk_level == RiskLevel.HEALTHY


def test_warning():
    p = _position(135.0)
    assert p.risk_level == RiskLevel.WARNING


def test_critical():
    p = _position(110.0, liquidatable=True)
    assert p.risk_level == RiskLevel.CRITICAL


def test_liquidation_boundary():
    assert _position(120.0).risk_level == RiskLevel.CRITICAL  # exactly at threshold = critical
    assert _position(120.1).risk_level == RiskLevel.WARNING
    assert _position(150.0).risk_level == RiskLevel.WARNING  # exactly at 150 = still warning
    assert _position(150.1).risk_level == RiskLevel.HEALTHY


# ── LTV ───────────────────────────────────────────────────────────────────


def test_ltv_ratio():
    p = Position(
        loan_id="x",
        borrower="0x0",
        collateral=15000,
        principal=10000,
        accrued_interest=0,
        health_factor=150.0,
        liquidatable=False,
        active=True,
    )
    assert abs(p.ltv - 10000 / 15000) < 0.001


def test_ltv_zero_collateral():
    p = _position(0.0)
    p.collateral = 0
    assert p.ltv == float("inf")


# ── RiskEvent ─────────────────────────────────────────────────────────────


def test_risk_event_serializes():
    event = RiskEvent(
        event_type=RiskEventType.HEALTH_FACTOR_DROP,
        loan_id="0xabc",
        borrower="0xdeadbeef",
        risk_level=RiskLevel.WARNING,
        health_factor=135.0,
        ltv=0.74,
        assessment={"output": "escalate", "risk_score": 0.6},
    )
    d = event.to_dict()
    assert d["event_type"] == "health_factor_drop"
    assert d["risk_level"] == "warning"
    assert d["health_factor"] == 135.0
    assert d["assessment"]["output"] == "escalate"
    assert "timestamp" in d


def test_nats_subject():
    event = RiskEvent(
        event_type=RiskEventType.LIQUIDATION_THRESHOLD,
        loan_id="x",
        borrower="0x0",
        risk_level=RiskLevel.CRITICAL,
        health_factor=110.0,
        ltv=0.9,
    )
    assert event.nats_subject() == "neotron.defi.risk.v1"


# ── Heuristic assessment ──────────────────────────────────────────────────


def test_heuristic_healthy():
    from neutron.defi.monitor import PositionMonitor

    m = PositionMonitor("", "")
    result = m._heuristic_assessment(_position(200.0))
    assert result["output"] == "approve"
    assert result["risk_score"] < 0.3


def test_heuristic_warning():
    from neutron.defi.monitor import PositionMonitor

    m = PositionMonitor("", "")
    # 130-150 = approve com fatores de alerta, risk_score > 0.2
    result = m._heuristic_assessment(_position(135.0))
    assert result["output"] == "approve"
    assert result["risk_score"] > 0.2
    assert len(result["risk_factors"]) > 0


def test_heuristic_critical():
    from neutron.defi.monitor import PositionMonitor

    m = PositionMonitor("", "")
    result = m._heuristic_assessment(_position(110.0, liquidatable=True))
    assert result["output"] == "deny"
    assert result["risk_score"] > 0.9


# ── Concurrent evaluation (sem chain) ────────────────────────────────────


def test_evaluate_skips_healthy():
    """evaluate() deve retornar None para posições saudáveis."""
    import asyncio
    from unittest.mock import patch

    from neutron.defi.monitor import PositionMonitor

    m = PositionMonitor("0xcontract", "http://localhost:8545")

    with patch.object(m, "fetch_position", return_value=_position(200.0)):
        result = asyncio.run(m.evaluate("0xabc"))
    assert result is None


def test_evaluate_emits_for_warning():
    """evaluate() deve retornar RiskEvent para posição em WARNING."""
    import asyncio
    from unittest.mock import patch

    from neutron.defi.monitor import PositionMonitor

    m = PositionMonitor("0xcontract", "http://localhost:8545")
    published = []

    async def mock_publish(subject, payload):
        published.append((subject, payload))
        return True

    with (
        patch.object(m, "fetch_position", return_value=_position(135.0)),
        patch("neutron.defi.monitor.publish", side_effect=mock_publish),
    ):
        event = asyncio.run(m.evaluate("0xabc"))

    assert event is not None
    assert event.risk_level == RiskLevel.WARNING
    assert len(published) == 1
    assert published[0][0] == "neotron.defi.risk.v1"
