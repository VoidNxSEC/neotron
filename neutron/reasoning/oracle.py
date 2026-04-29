"""
ORACLE Explainability Framework.

Provides multiple explanation strategies for agent decisions:
- Feature Importance: Ranks input features by their influence on the decision.
- Counterfactual: Generates "what if" scenarios showing how changes would alter outcomes.
- Example-Based: Explains decisions by referencing similar past cases.
- Chain of Thought: Traces the step-by-step reasoning process.
- Rule-Based: Maps decisions to deterministic rules that were applied.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ExplanationType(Enum):
    """Types of explanations supported by the ORACLE framework."""

    FEATURE_IMPORTANCE = "feature_importance"
    COUNTERFACTUAL = "counterfactual"
    EXAMPLE_BASED = "example_based"
    CHAIN_OF_THOUGHT = "chain_of_thought"
    RULE_BASED = "rule_based"


@dataclass
class ExplanationEvidence:
    """A single piece of evidence supporting an explanation."""

    feature: str
    value: Any
    importance: float
    description: str = ""


@dataclass
class ExplanationResult:
    """The result of an explanation, including evidence and rendering methods."""

    decision: str
    explanation_type: ExplanationType
    confidence: float
    evidence: list[ExplanationEvidence]
    reasoning: str
    counterfactuals: list[dict] = field(default_factory=list)

    def to_human_readable(self, max_evidence: int | None = None) -> str:
        """Convert the explanation to a human-readable text format."""
        lines: list[str] = []
        lines.append(f"Decision: {self.decision}")
        lines.append(f"Confidence: {self.confidence * 100:.1f}%")
        lines.append(f"Type: {self.explanation_type.value}")
        lines.append("")

        if not self.evidence:
            lines.append("No evidence available.")
        else:
            lines.append("Evidence:")
            display_evidence = self.evidence
            remaining = 0
            if max_evidence is not None and len(self.evidence) > max_evidence:
                display_evidence = self.evidence[:max_evidence]
                remaining = len(self.evidence) - max_evidence

            for e in display_evidence:
                lines.append(f"  - {e.feature}: {e.value} (importance: {e.importance})")
                if e.description:
                    lines.append(f"    {e.description}")

            if remaining > 0:
                lines.append(f"  ... and {remaining} more")

        lines.append("")
        lines.append(f"Reasoning: {self.reasoning}")

        if self.counterfactuals:
            lines.append("")
            lines.append("Counterfactuals:")
            for cf in self.counterfactuals:
                lines.append(f"  - {cf}")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Convert the explanation to a JSON string."""
        data = {
            "decision": self.decision,
            "explanation_type": self.explanation_type.value,
            "confidence": self.confidence,
            "evidence": [
                {
                    "feature": e.feature,
                    "value": e.value,
                    "importance": e.importance,
                    "description": e.description,
                }
                for e in self.evidence
            ],
            "reasoning": self.reasoning,
            "counterfactuals": self.counterfactuals,
        }
        return json.dumps(data, indent=2)

    def to_markdown(self) -> str:
        """Convert the explanation to Markdown format."""
        lines: list[str] = []
        lines.append("# Explanation")
        lines.append("")
        lines.append(f"## Decision: {self.decision}")
        lines.append("")
        lines.append(f"**Confidence:** {self.confidence * 100:.1f}%")
        lines.append("")
        lines.append(f"**Type:** {self.explanation_type.value}")
        lines.append("")

        if self.evidence:
            lines.append("## Evidence")
            lines.append("")
            lines.append("| Feature | Value | Importance | Description |")
            lines.append("|---------|-------|------------|-------------|")
            for e in self.evidence:
                lines.append(f"| {e.feature} | {e.value} | {e.importance} | {e.description} |")
            lines.append("")

        lines.append("## Reasoning")
        lines.append("")
        lines.append(self.reasoning)

        if self.counterfactuals:
            lines.append("")
            lines.append("## Counterfactuals")
            lines.append("")
            for cf in self.counterfactuals:
                items = ", ".join(f"**{k}**: {v}" for k, v in cf.items())
                lines.append(f"- {items}")

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Base explainer
# ---------------------------------------------------------------------------


class Explainer(ABC):
    """Abstract base class for all explainers."""

    @abstractmethod
    def explain(
        self,
        decision: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ExplanationResult: ...


# ---------------------------------------------------------------------------
# Concrete explainers
# ---------------------------------------------------------------------------


def _feature_importance_score(feature: str, value: Any, index: int, total: int) -> float:
    """Compute a deterministic importance score for a feature."""
    # Use a hash-based spread so different features get different scores
    h = abs(hash(feature)) % 1000
    score = (h + 1) / 1001.0
    # Clamp to [0, 1]
    return round(min(max(score, 0.0), 1.0), 4)


class FeatureImportanceExplainer(Explainer):
    """Explains decisions by ranking features by importance."""

    def explain(
        self,
        decision: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ExplanationResult:
        metadata = metadata or {}
        confidence = output_data.get("confidence", 0.5)
        total = len(input_data)

        evidence: list[ExplanationEvidence] = []
        for idx, (feature, value) in enumerate(input_data.items()):
            importance = _feature_importance_score(feature, value, idx, total)
            evidence.append(
                ExplanationEvidence(
                    feature=feature,
                    value=value,
                    importance=importance,
                    description=f"Feature '{feature}' with value {value}",
                )
            )

        # Sort by importance descending
        evidence.sort(key=lambda e: e.importance, reverse=True)

        top_features = ", ".join(e.feature for e in evidence[:3]) if evidence else "none"
        reasoning = (
            f"The decision '{decision}' was primarily influenced by: {top_features}. "
            f"Feature importance analysis identified {len(evidence)} contributing factors."
        )

        return ExplanationResult(
            decision=decision,
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )


class CounterfactualExplainer(Explainer):
    """Explains decisions by generating counterfactual scenarios."""

    def explain(
        self,
        decision: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ExplanationResult:
        metadata = metadata or {}
        confidence = output_data.get("confidence", 0.5)
        threshold = metadata.get("threshold")

        counterfactuals: list[dict] = []
        evidence: list[ExplanationEvidence] = []

        for feature, value in input_data.items():
            if threshold is not None and isinstance(value, (int, float)):
                # Generate a counterfactual below the threshold
                cf_value = threshold - 1 if isinstance(threshold, int) else threshold - 0.1
                counterfactuals.append({feature: cf_value, "outcome": f"opposite of '{decision}'"})
                evidence.append(
                    ExplanationEvidence(
                        feature=feature,
                        value=value,
                        importance=0.9,
                        description=(
                            f"If {feature} were {cf_value} (below threshold {threshold}), "
                            f"the decision would change."
                        ),
                    )
                )
            else:
                # Generate a generic counterfactual
                if isinstance(value, (int, float)):
                    cf_value_generic = value * 0.5
                else:
                    cf_value_generic = f"not_{value}"
                counterfactuals.append(
                    {feature: cf_value_generic, "outcome": f"opposite of '{decision}'"}
                )
                evidence.append(
                    ExplanationEvidence(
                        feature=feature,
                        value=value,
                        importance=0.8,
                        description=(
                            f"If {feature} were {cf_value_generic}, "
                            f"the decision would likely change."
                        ),
                    )
                )

        # Ensure at least one counterfactual even with empty input
        if not counterfactuals:
            counterfactuals.append(
                {"scenario": "alternative", "outcome": f"opposite of '{decision}'"}
            )

        reasoning = (
            f"Counterfactual analysis explores what if key factors were different. "
            f"The decision '{decision}' would change if the input values were altered as described."
        )

        return ExplanationResult(
            decision=decision,
            explanation_type=ExplanationType.COUNTERFACTUAL,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            counterfactuals=counterfactuals,
        )


class ExampleBasedExplainer(Explainer):
    """Explains decisions by referencing similar past cases."""

    def explain(
        self,
        decision: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ExplanationResult:
        metadata = metadata or {}
        confidence = output_data.get("confidence", 0.5)
        similar_cases: list[dict] = metadata.get("similar_cases", [])

        if not similar_cases:
            return ExplanationResult(
                decision=decision,
                explanation_type=ExplanationType.EXAMPLE_BASED,
                confidence=confidence,
                evidence=[],
                reasoning="No similar cases found in the knowledge base.",
            )

        # Sort by similarity descending
        sorted_cases = sorted(similar_cases, key=lambda c: c.get("similarity", 0), reverse=True)

        evidence: list[ExplanationEvidence] = []
        for case in sorted_cases:
            case_id = case.get("case_id", "unknown")
            outcome = case.get("outcome", "unknown")
            similarity = case.get("similarity", 0.0)
            evidence.append(
                ExplanationEvidence(
                    feature=f"case_{case_id}",
                    value=outcome,
                    importance=similarity,
                    description=f"Case {case_id}: outcome was '{outcome}' (similarity: {similarity})",
                )
            )

        case_ids = ", ".join(c.get("case_id", "?") for c in sorted_cases[:3])
        reasoning = (
            f"The decision '{decision}' is supported by {len(sorted_cases)} similar case(s): "
            f"{case_ids}. These cases had comparable inputs and similar outcomes."
        )

        return ExplanationResult(
            decision=decision,
            explanation_type=ExplanationType.EXAMPLE_BASED,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )


class ChainOfThoughtExplainer(Explainer):
    """Explains decisions by tracing the step-by-step reasoning process."""

    def explain(
        self,
        decision: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ExplanationResult:
        metadata = metadata or {}
        confidence = output_data.get("confidence", 0.5)
        reasoning_steps: list[str] = metadata.get("reasoning_steps", [])

        if not reasoning_steps:
            return ExplanationResult(
                decision=decision,
                explanation_type=ExplanationType.CHAIN_OF_THOUGHT,
                confidence=confidence,
                evidence=[],
                reasoning="No reasoning steps were provided for this decision.",
            )

        evidence: list[ExplanationEvidence] = []
        for idx, step in enumerate(reasoning_steps, start=1):
            evidence.append(
                ExplanationEvidence(
                    feature=f"step_{idx}",
                    value=idx,
                    importance=round(1.0 - (idx - 1) / max(len(reasoning_steps), 1), 4),
                    description=step,
                )
            )

        reasoning = (
            f"The decision '{decision}' was reached through {len(reasoning_steps)} "
            f"reasoning step(s): {' -> '.join(reasoning_steps)}"
        )

        return ExplanationResult(
            decision=decision,
            explanation_type=ExplanationType.CHAIN_OF_THOUGHT,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )


class RuleBasedExplainer(Explainer):
    """Explains decisions by mapping them to deterministic rules."""

    def explain(
        self,
        decision: str,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> ExplanationResult:
        metadata = metadata or {}
        confidence = output_data.get("confidence", 0.5)
        rules: list[str] = metadata.get("rules", [])

        if not rules:
            return ExplanationResult(
                decision=decision,
                explanation_type=ExplanationType.RULE_BASED,
                confidence=confidence,
                evidence=[],
                reasoning="No rules were provided for this decision.",
            )

        evidence: list[ExplanationEvidence] = []
        for idx, rule in enumerate(rules, start=1):
            evidence.append(
                ExplanationEvidence(
                    feature=f"rule_{idx}",
                    value=True,
                    importance=1.0,
                    description=rule,
                )
            )

        reasoning = (
            f"The decision '{decision}' was determined by {len(rules)} rule(s): " + "; ".join(rules)
        )

        return ExplanationResult(
            decision=decision,
            explanation_type=ExplanationType.RULE_BASED,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
        )


# ---------------------------------------------------------------------------
# Factory and convenience functions
# ---------------------------------------------------------------------------

_EXPLAINER_REGISTRY: dict[ExplanationType, type[Explainer]] = {
    ExplanationType.FEATURE_IMPORTANCE: FeatureImportanceExplainer,
    ExplanationType.COUNTERFACTUAL: CounterfactualExplainer,
    ExplanationType.EXAMPLE_BASED: ExampleBasedExplainer,
    ExplanationType.CHAIN_OF_THOUGHT: ChainOfThoughtExplainer,
    ExplanationType.RULE_BASED: RuleBasedExplainer,
}


def create_explainer(explanation_type: ExplanationType) -> Explainer:
    """Factory function to create an explainer by type.

    Raises:
        KeyError: If the explanation type is not registered.
    """
    cls = _EXPLAINER_REGISTRY[explanation_type]
    return cls()


def explain_agent_decision(
    decision: str,
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    explanation_type: ExplanationType,
    metadata: dict[str, Any] | None = None,
) -> ExplanationResult:
    """Convenience function to create an explainer and generate an explanation in one call."""
    metadata = metadata or {}
    explainer = create_explainer(explanation_type)
    return explainer.explain(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        metadata=metadata,
    )
