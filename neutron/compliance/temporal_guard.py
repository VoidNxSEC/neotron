"""
Temporal Guard — Layer 0 Compliance Pre-Guard

Integrates LangMath's TemporalReputation + CriticalDiscourseAnalyzer
as a pre-layer before neotron's SENTINEL to detect boiling-frog attacks:
gradual escalation of risk over time that traditional static guardrails miss.

Architecture:
  User Query
      |
  Layer 0: TEMPORAL (NEW)
    - Linguistic algebra → manipulation_score
    - Temporal reputation → decay-based trust tracking
    - Boiling frog detection → gradual escalation via linear regression
    - Dynamic threshold → adapts to agent behavior
    - Forensics DAG → incident analysis (optional)
      |
  Layer 1: SENTINEL (existing)
    - LGPD/GDPR guardrails
    - Compliance enforcement
      |
  ... (existing layers continue)

Usage:
    guard = TemporalGuard()
    verdict = guard.validate(agent_id="user_42", content="Some query")
    if not verdict.passed:
        logger.warning(f"Layer 0 blocked: {verdict.reason}")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from neutron.compliance.events import publish_sync
from neutron.langmath.linguistic_algebra import CriticalDiscourseAnalyzer
from neutron.langmath.temporal_reputation import TemporalReputation

logger = __import__("logging").getLogger("neutron.compliance.temporal_guard")


# ── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class TemporalVerdict:
    """Result of Layer 0 temporal guard validation."""

    passed: bool
    """Whether the query passed the temporal guard."""

    reputation: float
    """Current temporal reputation score (0.0–1.0)."""

    risk_score: float
    """Linguistic manipulation risk score (0.0–1.0)."""

    threshold: float
    """Dynamic threshold used for this decision."""

    escalation_detected: bool
    """Whether a gradual escalation (boiling frog) was detected."""

    escalation_slope: float = 0.0
    """Slope of the escalation trend (positive = increasing risk)."""

    manipulation_score: float = 0.0
    """Raw manipulation score from linguistic algebra."""

    reason: str = ""
    """Human-readable reason for the decision."""

    forensic_report: str | None = None
    """Optional forensic DAG analysis report."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional metadata for audit logging."""


@dataclass
class AgentTemporalState:
    """Persistent state for a single agent's temporal profile."""

    agent_id: str
    reputation: float = 0.5
    query_count: int = 0
    last_risk_scores: list[float] = field(default_factory=list)
    threshold: float = 0.7
    escalation_detected: bool = False


# ── Temporal Guard ───────────────────────────────────────────────────────────


class TemporalGuard:
    """
    Layer 0: Temporal + Linguistic Analysis Guard.

    Combines LangMath's linguistic algebra (CriticalDiscourseAnalyzer)
    with temporal reputation tracking (TemporalReputation) to detect
    boiling-frog attacks — gradual escalation of risk that builds trust
    before exploitation.

    LangMath is vendored under ``neutron.langmath`` so this guard has no
    runtime dependency on an external checkout.
    """

    def __init__(
        self,
        decay_rate: float = 0.001,
        learning_rate: float = 0.15,
        history_window: int = 100,
        enable_forensic: bool = True,
    ) -> None:
        self.enable_forensic = enable_forensic

        self.temporal_rep = TemporalReputation(
            decay_rate=decay_rate,
            learning_rate=learning_rate,
            history_window=history_window,
        )
        logger.info(
            "TemporalReputation initialized: decay=%.3f, lr=%.3f, window=%d",
            decay_rate,
            learning_rate,
            history_window,
        )
        self._has_full_langmath = True
        self.math_analyzer = CriticalDiscourseAnalyzer()

        # In-memory fallback state tracking (used in degraded mode)
        self._agent_states: dict[str, AgentTemporalState] = {}

    # ── Public API ───────────────────────────────────────────────────────

    def validate(
        self,
        agent_id: str,
        content: str,
        context: dict[str, Any] | None = None,
    ) -> TemporalVerdict:
        """
        Run Layer 0 temporal validation on an agent's query.

        Args:
            agent_id: Identifier for the agent/user.
            content: The query text to analyze.
            context: Optional metadata (e.g., source IP, session ID).

        Returns:
            TemporalVerdict with pass/fail decision.
        """
        if self._has_full_langmath:
            return self._validate_full(agent_id, content, context)
        return self._validate_degraded(agent_id, content, context)

    def get_agent_report(self, agent_id: str) -> str:
        """Generate a human-readable temporal report for an agent."""
        if self._has_full_langmath and self.temporal_rep is not None:
            try:
                return self.temporal_rep.get_agent_report(agent_id)
            except Exception as exc:
                logger.warning("get_agent_report failed: %s", exc)

        # Fallback report
        state = self._agent_states.get(agent_id)
        if state is None:
            return f"Agent {agent_id}: no temporal data available."
        return (
            f"Agent: {agent_id}\n"
            f"  Reputation: {state.reputation:.3f}\n"
            f"  Queries: {state.query_count}\n"
            f"  Threshold: {state.threshold:.3f}\n"
            f"  Escalation Detected: {state.escalation_detected}\n"
        )

    def get_agent_state(self, agent_id: str) -> AgentTemporalState | None:
        """Get the current temporal state for an agent."""
        if self._has_full_langmath and self.temporal_rep is not None:
            try:
                raw_state = self.temporal_rep._get_or_create_state(agent_id)
                threshold = self.temporal_rep.get_dynamic_threshold(agent_id)
                escalation = self.temporal_rep.detect_gradual_escalation(agent_id)
                return AgentTemporalState(
                    agent_id=agent_id,
                    reputation=raw_state.get("reputation", 0.5),
                    query_count=raw_state.get("total_queries", 0),
                    last_risk_scores=[event.risk_score for event in raw_state.get("history", [])],
                    threshold=threshold,
                    escalation_detected=escalation.get("escalation_detected", False),
                )
            except Exception:
                pass
        return self._agent_states.get(agent_id)

    # ── Full LangMath Validation ─────────────────────────────────────────

    def _validate_full(
        self,
        agent_id: str,
        content: str,
        context: dict[str, Any] | None,
    ) -> TemporalVerdict:
        """Validation using full LangMath linguistic algebra + reputation."""
        assert self.math_analyzer is not None
        assert self.temporal_rep is not None

        # 1. Linguistic analysis → manipulation score
        math_result = self.math_analyzer.analyze(content)
        manipulation_score = math_result.get("manipulation_score", 0.0)

        # 2. Update temporal reputation
        R, event = self.temporal_rep.update_reputation(
            agent_id=agent_id,
            query=content,
            risk_score=manipulation_score,
            was_blocked=False,
        )

        # 3. Detect gradual escalation (boiling frog)
        escalation = self.temporal_rep.detect_gradual_escalation(agent_id, window=5)
        escalation_detected = escalation.get("escalation_detected", False)
        slope = escalation.get("slope", 0.0)

        # 4. Get dynamic threshold
        threshold = self.temporal_rep.get_dynamic_threshold(agent_id)

        # 5. Check for trust exploitation
        trust_exploitation = self.temporal_rep.detect_trust_exploitation(agent_id)

        # 6. Decision
        passed = manipulation_score <= threshold

        # Build reason
        if passed:
            reason = (
                f"Temporal OK: risk={manipulation_score:.3f} <= "
                f"threshold={threshold:.3f}, R={R:.3f}"
            )
        else:
            reason = (
                f"Temporal BLOCKED: manipulation={manipulation_score:.3f} > "
                f"threshold={threshold:.3f}, R={R:.3f}"
            )

        if escalation_detected and passed:
            reason += f" | ⚠ Escalating (slope={slope:.3f}) but within threshold"
        elif escalation_detected:
            reason += f" | 🚨 Escalation detected (slope={slope:.3f})"

        # 7. Optional forensic report
        forensic_report: str | None = None
        if self.enable_forensic and (not passed or escalation_detected):
            try:
                from neutron.langmath.forensic_dag import ForensicDAG

                dag = ForensicDAG()
                forensic_report = dag.run_full_pipeline(content)
            except Exception as exc:
                logger.debug("ForensicDAG unavailable: %s", exc)

        # 8. Publish temporal event to NATS
        self._publish_temporal_event(
            agent_id=agent_id,
            passed=passed,
            reputation=R,
            risk_score=manipulation_score,
            threshold=threshold,
            escalation_detected=escalation_detected,
            slope=slope,
            trust_exploitation=trust_exploitation,
            context=context,
        )

        return TemporalVerdict(
            passed=passed,
            reputation=R,
            risk_score=manipulation_score,
            threshold=threshold,
            escalation_detected=escalation_detected,
            escalation_slope=slope,
            manipulation_score=manipulation_score,
            reason=reason,
            forensic_report=forensic_report,
            metadata={
                "linguistic_features": math_result,
                "trust_exploitation": trust_exploitation,
                "langmath_mode": "full",
            },
        )

    # ── Degraded Validation (no LangMath) ────────────────────────────────

    def _validate_degraded(
        self,
        agent_id: str,
        content: str,
        context: dict[str, Any] | None,
    ) -> TemporalVerdict:
        """
        Validation with basic heuristic checks when LangMath is unavailable.

        Uses simple heuristics instead of semantic analysis:
        - Query length as a rough proxy
        - Keyword-based risk indicators
        - In-memory state tracking with basic decay
        """
        if agent_id not in self._agent_states:
            self._agent_states[agent_id] = AgentTemporalState(agent_id=agent_id)

        state = self._agent_states[agent_id]

        # Simple risk heuristics
        risk_score = self._heuristic_risk(content)

        # Update state with decay
        state.reputation *= 0.99  # Simple decay
        state.last_risk_scores.append(risk_score)
        if len(state.last_risk_scores) > 10:
            state.last_risk_scores.pop(0)
        state.query_count += 1

        # Simple escalation detection
        if len(state.last_risk_scores) >= 3:
            recent = state.last_risk_scores[-3:]
            state.escalation_detected = all(
                recent[i] <= recent[i + 1] for i in range(len(recent) - 1)
            )

        # Dynamic threshold (lower for new agents, adapts over time)
        if state.query_count < 5:
            state.threshold = 0.5
        else:
            state.threshold = min(0.9, 0.5 + state.reputation * 0.4)

        passed = risk_score <= state.threshold
        slope = 0.0
        if len(state.last_risk_scores) >= 2:
            slope = state.last_risk_scores[-1] - state.last_risk_scores[-2]

        reason = (
            f"Temporal (degraded): risk={risk_score:.3f} "
            f"{'<=' if passed else '>'} threshold={state.threshold:.3f}"
        )

        self._publish_temporal_event(
            agent_id=agent_id,
            passed=passed,
            reputation=state.reputation,
            risk_score=risk_score,
            threshold=state.threshold,
            escalation_detected=state.escalation_detected,
            slope=slope,
            trust_exploitation={},
            context=context,
            degraded=True,
        )

        return TemporalVerdict(
            passed=passed,
            reputation=state.reputation,
            risk_score=risk_score,
            threshold=state.threshold,
            escalation_detected=state.escalation_detected,
            escalation_slope=slope,
            manipulation_score=risk_score,
            reason=reason,
            metadata={
                "langmath_mode": "degraded",
                "query_count": state.query_count,
            },
        )

    # ── Internal Helpers ────────────────────────────────────────────────

    @staticmethod
    def _heuristic_risk(content: str) -> float:
        """Basic heuristic risk scoring (used in degraded mode)."""
        if not content:
            return 0.0

        risk_indicators = [
            "export",
            "download",
            "copy",
            "transfer",
            "bypass",
            "override",
            "ignore",
            "disable",
            "password",
            "credential",
            "secret",
            "token",
            "all users",
            "all data",
            "all records",
        ]

        content_lower = content.lower()
        score = 0.0
        for indicator in risk_indicators:
            if indicator in content_lower:
                score += 0.1

        # Length penalty (very short or very long queries)
        words = content.split()
        if len(words) < 3:
            score += 0.05
        elif len(words) > 100:
            score += 0.1

        return min(score, 1.0)

    def _publish_temporal_event(
        self,
        agent_id: str,
        passed: bool,
        reputation: float,
        risk_score: float,
        threshold: float,
        escalation_detected: bool,
        slope: float,
        trust_exploitation: dict[str, Any],
        context: dict[str, Any] | None,
        degraded: bool = False,
    ) -> None:
        """Publish temporal guard verdict to NATS for owasaka SIEM ingestion."""
        event = {
            "guardrail_name": "temporal_guard",
            "regulation": "LAYER_0_TEMPORAL",
            "agent_id": agent_id,
            "passed": passed,
            "reputation": reputation,
            "risk_score": risk_score,
            "threshold": threshold,
            "escalation_detected": escalation_detected,
            "escalation_slope": slope,
            "trust_exploitation": trust_exploitation,
            "severity": "audit" if passed else "block",
            "langmath_mode": "degraded" if degraded else "full",
            "source": "neotron",
            "subject": "neotron.compliance.temporal.v1",
        }
        if context:
            event["context"] = context

        logger.info(json.dumps(event, ensure_ascii=False, default=str))
        publish_sync("neotron.compliance.temporal.v1", event)

        if not passed:
            # Also emit to the violation subject for SIEM alerting
            violation_event = {**event, "subject": "neotron.compliance.violation.v1"}
            publish_sync("neotron.compliance.violation.v1", violation_event)


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: TemporalGuard | None = None


def get_temporal_guard() -> TemporalGuard:
    """Get or create the singleton TemporalGuard instance."""
    global _instance
    if _instance is None:
        _instance = TemporalGuard()
    return _instance
