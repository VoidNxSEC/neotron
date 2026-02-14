from .oracle import (
    ChainOfThoughtExplainer,
    CounterfactualExplainer,
    ExampleBasedExplainer,
    ExplanationEvidence,
    ExplanationResult,
    ExplanationType,
    FeatureImportanceExplainer,
    RuleBasedExplainer,
    create_explainer,
    explain_agent_decision,
)

__all__ = [
    "ChainOfThoughtExplainer",
    "CounterfactualExplainer",
    "ExampleBasedExplainer",
    "ExplanationEvidence",
    "ExplanationResult",
    "ExplanationType",
    "FeatureImportanceExplainer",
    "RuleBasedExplainer",
    "create_explainer",
    "explain_agent_decision",
]

# Optional imports (require dspy dependency)
try:
    from .dspy_adapter import DSPyProviderAdapter, SimpleLLMProvider

    __all__.extend(["DSPyProviderAdapter", "SimpleLLMProvider"])
except ImportError:
    pass

try:
    from .ensemble_reasoning import EnsembleReasoner, EnsembleResult, ProviderResponse

    __all__.extend(["EnsembleReasoner", "EnsembleResult", "ProviderResponse"])
except ImportError:
    pass
