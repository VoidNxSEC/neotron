"""
ORACLE - Explainability Framework

Provides transparent, human-understandable explanations for AI agent decisions.

ORACLE enables:
- Multiple explanation strategies (feature importance, counterfactual, etc.)
- EU AI Act compliance (transparency requirements)
- Human-readable decision rationales
- Integration with CORTEX multi-agent system

Architecture:
┌─────────────────────────────────────────────────────────┐
│                    ORACLE Framework                     │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │  Explainer   │───▶│ Explanation  │───▶│ Renderer │ │
│  │  Strategy    │    │   Result     │    │          │ │
│  └──────────────┘    └──────────────┘    └──────────┘ │
│         │                    │                  │      │
│         ▼                    ▼                  ▼      │
│  Feature Importance   Structured Data    Human Text   │
│  Counterfactual       Confidence          JSON/HTML   │
│  Example-based        Reasoning           Markdown    │
│  Chain-of-Thought     Evidence                        │
└─────────────────────────────────────────────────────────┘

Example:
    >>> from neutron.reasoning import FeatureImportanceExplainer
    >>>
    >>> explainer = FeatureImportanceExplainer()
    >>> explanation = explainer.explain(
    ...     decision="Loan approved",
    ...     features={"credit_score": 750, "income": 80000},
    ...     model_output={"approved": True, "confidence": 0.92}
    ... )
    >>>
    >>> print(explanation.to_human_readable())
    # "Decision: Loan approved (92% confidence)
    #  Key factors:
    #  - Credit score (750): +35% influence
    #  - Income ($80,000): +28% influence"
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Protocol, Literal
from datetime import datetime
from abc import ABC, abstractmethod
import json


# =============================================================================
# Data Models
# =============================================================================

ExplanationType = Literal[
    "feature_importance",
    "counterfactual",
    "example_based",
    "chain_of_thought",
    "rule_based"
]


@dataclass
class ExplanationEvidence:
    """
    Evidence supporting an explanation

    Attributes:
        type: Type of evidence (feature, example, rule, etc.)
        value: Evidence value or description
        importance: Importance score (0.0-1.0)
        metadata: Additional evidence metadata
    """
    type: str
    value: Any
    importance: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate importance score"""
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(
                f"Importance must be between 0.0 and 1.0, got {self.importance}"
            )


@dataclass
class ExplanationResult:
    """
    Complete explanation of an AI decision

    Attributes:
        decision: The decision being explained
        explanation_type: Type of explanation strategy used
        confidence: Confidence in the decision (0.0-1.0)
        evidence: List of evidence supporting the decision
        reasoning: Human-readable reasoning text
        counterfactuals: Alternative scenarios (for counterfactual explanations)
        metadata: Additional explanation metadata
        timestamp: When explanation was generated
    """
    decision: str
    explanation_type: ExplanationType
    confidence: float
    evidence: List[ExplanationEvidence] = field(default_factory=list)
    reasoning: str = ""
    counterfactuals: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Validate confidence score"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def to_human_readable(self, max_evidence: int = 5) -> str:
        """
        Convert explanation to human-readable text

        Args:
            max_evidence: Maximum number of evidence items to include

        Returns:
            Human-readable explanation text
        """
        lines = [
            f"Decision: {self.decision}",
            f"Confidence: {self.confidence:.0%}",
            f"Explanation Type: {self.explanation_type}",
        ]

        if self.reasoning:
            lines.append(f"\nReasoning:\n{self.reasoning}")

        if self.evidence:
            lines.append(f"\nKey Evidence:")
            # Sort by importance (descending)
            sorted_evidence = sorted(
                self.evidence,
                key=lambda e: e.importance,
                reverse=True
            )
            for i, ev in enumerate(sorted_evidence[:max_evidence], 1):
                lines.append(
                    f"  {i}. {ev.type}: {ev.value} "
                    f"(importance: {ev.importance:.0%})"
                )

        if self.counterfactuals:
            lines.append(f"\nAlternative Scenarios:")
            for i, cf in enumerate(self.counterfactuals, 1):
                lines.append(f"  {i}. {cf.get('description', cf)}")

        return "\n".join(lines)

    def to_json(self) -> str:
        """
        Convert explanation to JSON format

        Returns:
            JSON string representation
        """
        data = {
            "decision": self.decision,
            "explanation_type": self.explanation_type,
            "confidence": self.confidence,
            "evidence": [
                {
                    "type": e.type,
                    "value": str(e.value),
                    "importance": e.importance,
                    "metadata": e.metadata
                }
                for e in self.evidence
            ],
            "reasoning": self.reasoning,
            "counterfactuals": self.counterfactuals,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
        return json.dumps(data, indent=2)

    def to_markdown(self) -> str:
        """
        Convert explanation to Markdown format

        Returns:
            Markdown string representation
        """
        lines = [
            f"# Decision Explanation",
            f"",
            f"**Decision:** {self.decision}  ",
            f"**Confidence:** {self.confidence:.0%}  ",
            f"**Type:** {self.explanation_type}  ",
            f"**Generated:** {self.timestamp.isoformat()}  ",
        ]

        if self.reasoning:
            lines.extend([
                f"",
                f"## Reasoning",
                f"",
                self.reasoning
            ])

        if self.evidence:
            lines.extend([
                f"",
                f"## Evidence",
                f""
            ])
            sorted_evidence = sorted(
                self.evidence,
                key=lambda e: e.importance,
                reverse=True
            )
            for i, ev in enumerate(sorted_evidence, 1):
                lines.append(
                    f"{i}. **{ev.type}**: {ev.value} "
                    f"({ev.importance:.0%} importance)"
                )

        if self.counterfactuals:
            lines.extend([
                f"",
                f"## Alternative Scenarios",
                f""
            ])
            for i, cf in enumerate(self.counterfactuals, 1):
                desc = cf.get('description', str(cf))
                lines.append(f"{i}. {desc}")

        return "\n".join(lines)


# =============================================================================
# Explainer Protocol
# =============================================================================

class Explainer(Protocol):
    """
    Protocol for explanation strategies

    All explainers must implement the explain() method.
    """

    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate explanation for a decision

        Args:
            decision: The decision being explained
            input_data: Input features/data that led to decision
            output_data: Model/agent output data
            metadata: Additional context

        Returns:
            ExplanationResult with complete explanation
        """
        ...


# =============================================================================
# Base Explainer
# =============================================================================

class BaseExplainer(ABC):
    """
    Abstract base class for explainers

    Provides common functionality for all explanation strategies.
    """

    def __init__(self, name: str, explanation_type: ExplanationType):
        """
        Initialize explainer

        Args:
            name: Human-readable name
            explanation_type: Type of explanation this generates
        """
        self.name = name
        self.explanation_type = explanation_type

    @abstractmethod
    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate explanation (must be implemented by subclasses)

        Args:
            decision: The decision being explained
            input_data: Input features/data
            output_data: Model/agent output
            metadata: Additional context

        Returns:
            ExplanationResult
        """
        pass

    def _extract_confidence(self, output_data: Dict[str, Any]) -> float:
        """
        Extract confidence score from output data

        Args:
            output_data: Model/agent output

        Returns:
            Confidence score (0.0-1.0)
        """
        # Try common confidence field names
        for key in ["confidence", "probability", "score", "certainty"]:
            if key in output_data:
                return float(output_data[key])

        # Default to 0.5 if no confidence found
        return 0.5

    def _create_evidence(
        self,
        type: str,
        value: Any,
        importance: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationEvidence:
        """
        Create evidence object

        Args:
            type: Evidence type
            value: Evidence value
            importance: Importance score
            metadata: Additional metadata

        Returns:
            ExplanationEvidence
        """
        return ExplanationEvidence(
            type=type,
            value=value,
            importance=importance,
            metadata=metadata or {}
        )


# =============================================================================
# Feature Importance Explainer
# =============================================================================

class FeatureImportanceExplainer(BaseExplainer):
    """
    Explains decisions based on input feature importance

    Shows which input features had the most impact on the decision.

    Example:
        >>> explainer = FeatureImportanceExplainer()
        >>> explanation = explainer.explain(
        ...     decision="Loan approved",
        ...     input_data={"credit_score": 750, "income": 80000, "debt": 5000},
        ...     output_data={"approved": True, "confidence": 0.92}
        ... )
    """

    def __init__(self):
        """Initialize feature importance explainer"""
        super().__init__(
            name="Feature Importance Explainer",
            explanation_type="feature_importance"
        )

    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate feature importance explanation

        Args:
            decision: The decision
            input_data: Input features
            output_data: Model output with optional feature_importances
            metadata: Additional context

        Returns:
            ExplanationResult with feature importance evidence
        """
        confidence = self._extract_confidence(output_data)

        # Get feature importances (from model if available, else heuristic)
        feature_importances = output_data.get("feature_importances", {})

        if not feature_importances:
            # Heuristic: assume all features equally important
            feature_importances = {
                key: 1.0 / len(input_data)
                for key in input_data.keys()
            }

        # Create evidence for each feature
        evidence = []
        for feature, value in input_data.items():
            importance = feature_importances.get(feature, 0.0)
            evidence.append(
                self._create_evidence(
                    type=feature,
                    value=value,
                    importance=importance,
                    metadata={"feature_name": feature}
                )
            )

        # Generate reasoning text
        top_features = sorted(
            evidence,
            key=lambda e: e.importance,
            reverse=True
        )[:3]

        reasoning_lines = [
            f"The decision '{decision}' was primarily influenced by:"
        ]
        for i, ev in enumerate(top_features, 1):
            reasoning_lines.append(
                f"{i}. {ev.type} = {ev.value} "
                f"({ev.importance:.0%} influence)"
            )

        reasoning = "\n".join(reasoning_lines)

        return ExplanationResult(
            decision=decision,
            explanation_type=self.explanation_type,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            metadata=metadata or {}
        )


# =============================================================================
# Simple Rule-Based Explainer
# =============================================================================

class RuleBasedExplainer(BaseExplainer):
    """
    Explains decisions using if-then rules

    Useful for transparent, auditable decision-making.

    Example:
        >>> explainer = RuleBasedExplainer()
        >>> explanation = explainer.explain(
        ...     decision="Loan approved",
        ...     input_data={"credit_score": 750},
        ...     output_data={"approved": True, "confidence": 1.0},
        ...     metadata={"rules": [
        ...         "IF credit_score >= 700 THEN approve"
        ...     ]}
        ... )
    """

    def __init__(self):
        """Initialize rule-based explainer"""
        super().__init__(
            name="Rule-Based Explainer",
            explanation_type="rule_based"
        )

    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate rule-based explanation

        Args:
            decision: The decision
            input_data: Input data
            output_data: Model output
            metadata: Must contain 'rules' or 'applied_rules'

        Returns:
            ExplanationResult with rules as evidence
        """
        confidence = self._extract_confidence(output_data)
        metadata = metadata or {}

        # Get rules from metadata
        rules = metadata.get("rules", metadata.get("applied_rules", []))

        # Create evidence for each rule
        evidence = []
        for i, rule in enumerate(rules):
            evidence.append(
                self._create_evidence(
                    type="rule",
                    value=rule,
                    importance=1.0 / len(rules) if rules else 1.0,
                    metadata={"rule_index": i}
                )
            )

        # Generate reasoning
        if rules:
            reasoning = f"The decision '{decision}' was made based on:\n"
            reasoning += "\n".join(f"  - {rule}" for rule in rules)
        else:
            reasoning = f"Decision: {decision} (no explicit rules provided)"

        return ExplanationResult(
            decision=decision,
            explanation_type=self.explanation_type,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            metadata=metadata
        )


# =============================================================================
# Counterfactual Explainer
# =============================================================================

class CounterfactualExplainer(BaseExplainer):
    """
    Explains decisions by showing what would need to change for a different outcome

    "What if" scenarios help users understand decision boundaries.

    Example:
        >>> explainer = CounterfactualExplainer()
        >>> explanation = explainer.explain(
        ...     decision="Loan denied",
        ...     input_data={"credit_score": 650, "income": 40000},
        ...     output_data={"approved": False, "confidence": 0.85},
        ...     metadata={"counterfactuals": [
        ...         {"credit_score": 700, "outcome": "approved"},
        ...         {"income": 60000, "outcome": "approved"}
        ...     ]}
        ... )
    """

    def __init__(self):
        """Initialize counterfactual explainer"""
        super().__init__(
            name="Counterfactual Explainer",
            explanation_type="counterfactual"
        )

    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate counterfactual explanation

        Args:
            decision: The decision
            input_data: Original input data
            output_data: Model output
            metadata: Should contain 'counterfactuals' list

        Returns:
            ExplanationResult with counterfactual scenarios
        """
        confidence = self._extract_confidence(output_data)
        metadata = metadata or {}

        # Get counterfactuals from metadata or generate simple ones
        counterfactuals = metadata.get("counterfactuals", [])

        # Create evidence for current decision
        evidence = [
            self._create_evidence(
                type=key,
                value=value,
                importance=0.8,
                metadata={"current_value": True}
            )
            for key, value in input_data.items()
        ]

        # Generate reasoning with counterfactuals
        reasoning_lines = [f"Current decision: {decision}"]

        if counterfactuals:
            reasoning_lines.append("\nAlternative scenarios:")
            for i, cf in enumerate(counterfactuals, 1):
                changes = cf.get("changes", cf)
                outcome = cf.get("outcome", "different outcome")
                reasoning_lines.append(
                    f"  {i}. If {changes} → {outcome}"
                )
        else:
            reasoning_lines.append(
                "\n(No counterfactual scenarios provided)"
            )

        reasoning = "\n".join(reasoning_lines)

        return ExplanationResult(
            decision=decision,
            explanation_type=self.explanation_type,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            counterfactuals=counterfactuals,
            metadata=metadata
        )


# =============================================================================
# Example-Based Explainer
# =============================================================================

class ExampleBasedExplainer(BaseExplainer):
    """
    Explains decisions by referencing similar past cases

    Shows how similar inputs were handled previously.

    Example:
        >>> explainer = ExampleBasedExplainer()
        >>> explanation = explainer.explain(
        ...     decision="High risk customer",
        ...     input_data={"transaction_amount": 10000, "frequency": "rare"},
        ...     output_data={"risk_level": "high", "confidence": 0.78},
        ...     metadata={"similar_examples": [
        ...         {"case_id": "case_001", "similarity": 0.92, "outcome": "high_risk"},
        ...         {"case_id": "case_087", "similarity": 0.88, "outcome": "high_risk"}
        ...     ]}
        ... )
    """

    def __init__(self):
        """Initialize example-based explainer"""
        super().__init__(
            name="Example-Based Explainer",
            explanation_type="example_based"
        )

    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate example-based explanation

        Args:
            decision: The decision
            input_data: Current input
            output_data: Model output
            metadata: Should contain 'similar_examples' list

        Returns:
            ExplanationResult with similar examples as evidence
        """
        confidence = self._extract_confidence(output_data)
        metadata = metadata or {}

        # Get similar examples
        similar_examples = metadata.get("similar_examples", [])

        # Create evidence for each example
        evidence = []
        for i, example in enumerate(similar_examples):
            similarity = example.get("similarity", 0.5)
            case_id = example.get("case_id", f"example_{i}")
            outcome = example.get("outcome", "unknown")

            evidence.append(
                self._create_evidence(
                    type="similar_case",
                    value=f"{case_id}: {outcome}",
                    importance=similarity,
                    metadata=example
                )
            )

        # Generate reasoning
        if similar_examples:
            reasoning_lines = [
                f"Decision '{decision}' is similar to {len(similar_examples)} past cases:"
            ]
            for i, ex in enumerate(similar_examples[:5], 1):
                case_id = ex.get("case_id", f"case_{i}")
                similarity = ex.get("similarity", 0.0)
                outcome = ex.get("outcome", "N/A")
                reasoning_lines.append(
                    f"  {i}. {case_id}: {outcome} ({similarity:.0%} similar)"
                )
        else:
            reasoning = f"Decision: {decision} (no similar examples found)"
            reasoning_lines = [reasoning]

        reasoning = "\n".join(reasoning_lines)

        return ExplanationResult(
            decision=decision,
            explanation_type=self.explanation_type,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            metadata=metadata
        )


# =============================================================================
# Chain-of-Thought Explainer
# =============================================================================

class ChainOfThoughtExplainer(BaseExplainer):
    """
    Explains decisions by showing step-by-step reasoning process

    Particularly useful for LLM-based agents that can generate reasoning traces.

    Example:
        >>> explainer = ChainOfThoughtExplainer()
        >>> explanation = explainer.explain(
        ...     decision="Approve transaction",
        ...     input_data={"amount": 500, "merchant": "Amazon"},
        ...     output_data={"approved": True, "confidence": 0.95},
        ...     metadata={"reasoning_steps": [
        ...         "Step 1: Check transaction amount ($500) - within normal range",
        ...         "Step 2: Verify merchant (Amazon) - trusted",
        ...         "Step 3: Check user history - no fraud flags",
        ...         "Conclusion: Approve transaction"
        ...     ]}
        ... )
    """

    def __init__(self):
        """Initialize chain-of-thought explainer"""
        super().__init__(
            name="Chain-of-Thought Explainer",
            explanation_type="chain_of_thought"
        )

    def explain(
        self,
        decision: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ExplanationResult:
        """
        Generate chain-of-thought explanation

        Args:
            decision: The decision
            input_data: Input data
            output_data: Model output
            metadata: Should contain 'reasoning_steps' or 'chain_of_thought'

        Returns:
            ExplanationResult with reasoning steps as evidence
        """
        confidence = self._extract_confidence(output_data)
        metadata = metadata or {}

        # Get reasoning steps
        reasoning_steps = metadata.get(
            "reasoning_steps",
            metadata.get("chain_of_thought", [])
        )

        # Create evidence for each reasoning step
        evidence = []
        for i, step in enumerate(reasoning_steps):
            evidence.append(
                self._create_evidence(
                    type="reasoning_step",
                    value=step,
                    importance=1.0 / len(reasoning_steps) if reasoning_steps else 1.0,
                    metadata={"step_number": i + 1}
                )
            )

        # Generate reasoning text
        if reasoning_steps:
            reasoning = "Decision reasoning chain:\n\n"
            reasoning += "\n".join(
                f"Step {i}: {step}"
                for i, step in enumerate(reasoning_steps, 1)
            )
            reasoning += f"\n\nFinal decision: {decision}"
        else:
            reasoning = f"Decision: {decision}\n(No reasoning steps provided)"

        return ExplanationResult(
            decision=decision,
            explanation_type=self.explanation_type,
            confidence=confidence,
            evidence=evidence,
            reasoning=reasoning,
            metadata=metadata
        )


# =============================================================================
# Utility Functions
# =============================================================================

def create_explainer(explanation_type: ExplanationType) -> BaseExplainer:
    """
    Factory function to create explainer by type

    Args:
        explanation_type: Type of explainer to create

    Returns:
        Explainer instance

    Raises:
        ValueError: If explanation type not recognized
    """
    explainers = {
        "feature_importance": FeatureImportanceExplainer,
        "counterfactual": CounterfactualExplainer,
        "example_based": ExampleBasedExplainer,
        "chain_of_thought": ChainOfThoughtExplainer,
        "rule_based": RuleBasedExplainer,
    }

    if explanation_type not in explainers:
        raise ValueError(
            f"Unknown explanation type: {explanation_type}. "
            f"Available: {list(explainers.keys())}"
        )

    return explainers[explanation_type]()


def explain_agent_decision(
    agent_output: str,
    input_data: Dict[str, Any],
    output_metadata: Dict[str, Any],
    explanation_type: ExplanationType = "feature_importance"
) -> ExplanationResult:
    """
    Convenience function to explain an agent decision

    Args:
        agent_output: The agent's decision/output
        input_data: Input that led to the decision
        output_metadata: Agent output metadata (confidence, etc.)
        explanation_type: Type of explanation to generate

    Returns:
        ExplanationResult

    Example:
        >>> explanation = explain_agent_decision(
        ...     agent_output="Approve loan application",
        ...     input_data={"credit_score": 750, "income": 80000},
        ...     output_metadata={"confidence": 0.92},
        ...     explanation_type="feature_importance"
        ... )
    """
    explainer = create_explainer(explanation_type)

    return explainer.explain(
        decision=agent_output,
        input_data=input_data,
        output_data=output_metadata
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Data models
    "ExplanationType",
    "ExplanationEvidence",
    "ExplanationResult",

    # Protocols and base classes
    "Explainer",
    "BaseExplainer",

    # Concrete explainers
    "FeatureImportanceExplainer",
    "CounterfactualExplainer",
    "ExampleBasedExplainer",
    "ChainOfThoughtExplainer",
    "RuleBasedExplainer",

    # Utility functions
    "create_explainer",
    "explain_agent_decision",
]
