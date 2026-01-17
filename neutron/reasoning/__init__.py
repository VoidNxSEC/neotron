"""
ORACLE Reasoning & Explainability Framework

Provides transparent explanations for AI agent decisions to ensure
compliance with EU AI Act transparency requirements.

Components:
- ORACLE: Core explainability framework
- Multiple explanation strategies
- Human-readable output rendering
- Integration with CORTEX agents

Example:
    >>> from neutron.reasoning import FeatureImportanceExplainer
    >>>
    >>> explainer = FeatureImportanceExplainer()
    >>> explanation = explainer.explain(
    ...     decision="Loan approved",
    ...     input_data={"credit_score": 750},
    ...     output_data={"confidence": 0.92}
    ... )
    >>>
    >>> print(explanation.to_human_readable())
"""

from neutron.reasoning.oracle import (
    # Data models
    ExplanationType,
    ExplanationEvidence,
    ExplanationResult,

    # Protocols and base classes
    Explainer,
    BaseExplainer,

    # Concrete explainers
    FeatureImportanceExplainer,
    CounterfactualExplainer,
    ExampleBasedExplainer,
    ChainOfThoughtExplainer,
    RuleBasedExplainer,

    # Utility functions
    create_explainer,
    explain_agent_decision,
)

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
