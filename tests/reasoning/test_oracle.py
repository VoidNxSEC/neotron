"""
Tests for ORACLE Explainability Framework.

Tests cover:
- ExplanationResult data model and rendering methods
- ExplanationEvidence data model
- All 5 explainer strategies
- Factory function
- Convenience functions
"""

from typing import Any, Dict, List
import json
import pytest

from neutron.reasoning import (
    ExplanationType,
    ExplanationEvidence,
    ExplanationResult,
    Explainer,
    BaseExplainer,
    FeatureImportanceExplainer,
    CounterfactualExplainer,
    ExampleBasedExplainer,
    ChainOfThoughtExplainer,
    RuleBasedExplainer,
    create_explainer,
    explain_agent_decision,
)


# ============================================================================
# ExplanationEvidence Tests
# ============================================================================


def test_explanation_evidence_creation():
    """Test creating ExplanationEvidence with all fields."""
    evidence = ExplanationEvidence(
        feature="credit_score",
        value=750,
        importance=0.85,
        description="High credit score positively influences approval"
    )

    assert evidence.feature == "credit_score"
    assert evidence.value == 750
    assert evidence.importance == 0.85
    assert "High credit score" in evidence.description


def test_explanation_evidence_minimal():
    """Test creating ExplanationEvidence with minimal fields."""
    evidence = ExplanationEvidence(
        feature="age",
        value=25,
        importance=0.3
    )

    assert evidence.feature == "age"
    assert evidence.value == 25
    assert evidence.importance == 0.3
    assert evidence.description == ""


# ============================================================================
# ExplanationResult Tests
# ============================================================================


def test_explanation_result_creation():
    """Test creating ExplanationResult with all fields."""
    evidence_list = [
        ExplanationEvidence(
            feature="credit_score",
            value=750,
            importance=0.85,
            description="High credit score"
        ),
        ExplanationEvidence(
            feature="income",
            value=80000,
            importance=0.75,
            description="High income"
        )
    ]

    result = ExplanationResult(
        decision="Loan approved",
        explanation_type=ExplanationType.FEATURE_IMPORTANCE,
        confidence=0.92,
        evidence=evidence_list,
        reasoning="Strong financial indicators support approval",
        counterfactuals=[
            {"credit_score": 600, "outcome": "Loan denied"}
        ]
    )

    assert result.decision == "Loan approved"
    assert result.explanation_type == ExplanationType.FEATURE_IMPORTANCE
    assert result.confidence == 0.92
    assert len(result.evidence) == 2
    assert len(result.counterfactuals) == 1


def test_explanation_result_to_human_readable():
    """Test converting ExplanationResult to human-readable text."""
    evidence_list = [
        ExplanationEvidence(
            feature="credit_score",
            value=750,
            importance=0.85,
            description="High credit score"
        )
    ]

    result = ExplanationResult(
        decision="Loan approved",
        explanation_type=ExplanationType.FEATURE_IMPORTANCE,
        confidence=0.92,
        evidence=evidence_list,
        reasoning="Strong financial indicators",
        counterfactuals=[]
    )

    human_text = result.to_human_readable()

    assert "Loan approved" in human_text
    assert "92.0%" in human_text
    assert "credit_score" in human_text
    assert "750" in human_text
    assert "0.85" in human_text
    assert "Strong financial indicators" in human_text


def test_explanation_result_to_human_readable_with_max_evidence():
    """Test human-readable output with max_evidence limit."""
    evidence_list = [
        ExplanationEvidence(f"feature_{i}", i, 0.5, f"desc {i}")
        for i in range(10)
    ]

    result = ExplanationResult(
        decision="Test decision",
        explanation_type=ExplanationType.FEATURE_IMPORTANCE,
        confidence=0.8,
        evidence=evidence_list,
        reasoning="Test reasoning",
        counterfactuals=[]
    )

    human_text = result.to_human_readable(max_evidence=3)

    # Should show first 3 evidence items
    assert "feature_0" in human_text
    assert "feature_1" in human_text
    assert "feature_2" in human_text
    # Should indicate truncation
    assert "7 more" in human_text or "..." in human_text


def test_explanation_result_to_json():
    """Test converting ExplanationResult to JSON."""
    evidence_list = [
        ExplanationEvidence(
            feature="credit_score",
            value=750,
            importance=0.85,
            description="High credit score"
        )
    ]

    result = ExplanationResult(
        decision="Loan approved",
        explanation_type=ExplanationType.FEATURE_IMPORTANCE,
        confidence=0.92,
        evidence=evidence_list,
        reasoning="Strong indicators",
        counterfactuals=[{"credit_score": 600, "outcome": "denied"}]
    )

    json_str = result.to_json()
    parsed = json.loads(json_str)

    assert parsed["decision"] == "Loan approved"
    assert parsed["explanation_type"] == "feature_importance"
    assert parsed["confidence"] == 0.92
    assert len(parsed["evidence"]) == 1
    assert parsed["evidence"][0]["feature"] == "credit_score"
    assert len(parsed["counterfactuals"]) == 1


def test_explanation_result_to_markdown():
    """Test converting ExplanationResult to Markdown."""
    evidence_list = [
        ExplanationEvidence(
            feature="credit_score",
            value=750,
            importance=0.85,
            description="High credit score"
        ),
        ExplanationEvidence(
            feature="income",
            value=80000,
            importance=0.75,
            description="High income"
        )
    ]

    result = ExplanationResult(
        decision="Loan approved",
        explanation_type=ExplanationType.FEATURE_IMPORTANCE,
        confidence=0.92,
        evidence=evidence_list,
        reasoning="Strong financial indicators",
        counterfactuals=[{"credit_score": 600, "outcome": "denied"}]
    )

    markdown = result.to_markdown()

    # Check for Markdown formatting
    assert "# Explanation" in markdown or "## Decision" in markdown
    assert "Loan approved" in markdown
    assert "**" in markdown  # Bold text
    assert "credit_score" in markdown
    assert "income" in markdown
    assert "counterfactual" in markdown.lower() or "600" in markdown


def test_explanation_result_empty_evidence():
    """Test ExplanationResult with no evidence."""
    result = ExplanationResult(
        decision="Decision made",
        explanation_type=ExplanationType.RULE_BASED,
        confidence=0.5,
        evidence=[],
        reasoning="No specific evidence",
        counterfactuals=[]
    )

    human_text = result.to_human_readable()
    assert "Decision made" in human_text
    assert "No evidence" in human_text or "0 evidence" in human_text or len(result.evidence) == 0


# ============================================================================
# FeatureImportanceExplainer Tests
# ============================================================================


def test_feature_importance_explainer_basic():
    """Test basic feature importance explanation."""
    explainer = FeatureImportanceExplainer()

    input_data = {
        "credit_score": 750,
        "income": 80000,
        "age": 35
    }
    output_data = {
        "confidence": 0.92,
        "decision": "approved"
    }

    result = explainer.explain(
        decision="Loan approved",
        input_data=input_data,
        output_data=output_data
    )

    assert result.decision == "Loan approved"
    assert result.explanation_type == ExplanationType.FEATURE_IMPORTANCE
    assert result.confidence == 0.92
    assert len(result.evidence) == 3  # 3 input features

    # Check evidence is sorted by importance (descending)
    importances = [e.importance for e in result.evidence]
    assert importances == sorted(importances, reverse=True)


def test_feature_importance_explainer_single_feature():
    """Test feature importance with single feature."""
    explainer = FeatureImportanceExplainer()

    result = explainer.explain(
        decision="Simple decision",
        input_data={"score": 100},
        output_data={"confidence": 0.8}
    )

    assert len(result.evidence) == 1
    assert result.evidence[0].feature == "score"
    assert result.evidence[0].value == 100


def test_feature_importance_explainer_no_confidence():
    """Test feature importance without confidence in output."""
    explainer = FeatureImportanceExplainer()

    result = explainer.explain(
        decision="Decision",
        input_data={"feature": "value"},
        output_data={}
    )

    # Should use default confidence
    assert 0.0 <= result.confidence <= 1.0


# ============================================================================
# CounterfactualExplainer Tests
# ============================================================================


def test_counterfactual_explainer_basic():
    """Test basic counterfactual explanation."""
    explainer = CounterfactualExplainer()

    input_data = {"credit_score": 750, "income": 80000}
    output_data = {"confidence": 0.92}
    metadata = {"threshold": 700}

    result = explainer.explain(
        decision="Loan approved",
        input_data=input_data,
        output_data=output_data,
        metadata=metadata
    )

    assert result.decision == "Loan approved"
    assert result.explanation_type == ExplanationType.COUNTERFACTUAL
    assert result.confidence == 0.92
    assert len(result.counterfactuals) > 0

    # Check reasoning mentions "what if"
    assert "what if" in result.reasoning.lower() or "would" in result.reasoning.lower()


def test_counterfactual_explainer_with_threshold():
    """Test counterfactual generates scenarios below threshold."""
    explainer = CounterfactualExplainer()

    metadata = {"threshold": 700}

    result = explainer.explain(
        decision="Approved",
        input_data={"credit_score": 750},
        output_data={"confidence": 0.9},
        metadata=metadata
    )

    # Should have counterfactual with credit_score below threshold
    assert any(
        cf.get("credit_score", 0) < 700
        for cf in result.counterfactuals
    )


def test_counterfactual_explainer_no_metadata():
    """Test counterfactual explanation without metadata."""
    explainer = CounterfactualExplainer()

    result = explainer.explain(
        decision="Decision",
        input_data={"feature": 100},
        output_data={"confidence": 0.8},
        metadata={}
    )

    # Should still generate counterfactuals
    assert len(result.counterfactuals) > 0


# ============================================================================
# ExampleBasedExplainer Tests
# ============================================================================


def test_example_based_explainer_with_examples():
    """Test example-based explanation with similar cases."""
    explainer = ExampleBasedExplainer()

    metadata = {
        "similar_cases": [
            {"case_id": "A001", "outcome": "approved", "similarity": 0.95},
            {"case_id": "A002", "outcome": "approved", "similarity": 0.88}
        ]
    }

    result = explainer.explain(
        decision="Loan approved",
        input_data={"credit_score": 750},
        output_data={"confidence": 0.9},
        metadata=metadata
    )

    assert result.decision == "Loan approved"
    assert result.explanation_type == ExplanationType.EXAMPLE_BASED
    assert len(result.evidence) == 2  # 2 similar cases

    # Check evidence mentions case IDs
    evidence_text = " ".join([e.description for e in result.evidence])
    assert "A001" in evidence_text
    assert "A002" in evidence_text


def test_example_based_explainer_no_examples():
    """Test example-based explanation without similar cases."""
    explainer = ExampleBasedExplainer()

    result = explainer.explain(
        decision="Decision",
        input_data={"feature": 100},
        output_data={"confidence": 0.8},
        metadata={}
    )

    # Should indicate no similar cases
    assert "No similar" in result.reasoning or "not found" in result.reasoning.lower()
    assert len(result.evidence) == 0


def test_example_based_explainer_sorts_by_similarity():
    """Test that examples are sorted by similarity."""
    explainer = ExampleBasedExplainer()

    metadata = {
        "similar_cases": [
            {"case_id": "A", "outcome": "yes", "similarity": 0.7},
            {"case_id": "B", "outcome": "yes", "similarity": 0.9},
            {"case_id": "C", "outcome": "yes", "similarity": 0.8},
        ]
    }

    result = explainer.explain(
        decision="Decision",
        input_data={},
        output_data={"confidence": 0.8},
        metadata=metadata
    )

    # Evidence should be sorted by importance (similarity) descending
    importances = [e.importance for e in result.evidence]
    assert importances == sorted(importances, reverse=True)

    # First evidence should be case B (0.9 similarity)
    assert "B" in result.evidence[0].description


# ============================================================================
# ChainOfThoughtExplainer Tests
# ============================================================================


def test_chain_of_thought_explainer_with_steps():
    """Test chain-of-thought explanation with reasoning steps."""
    explainer = ChainOfThoughtExplainer()

    metadata = {
        "reasoning_steps": [
            "Step 1: Verify credit score is above 700",
            "Step 2: Check income meets minimum requirement",
            "Step 3: Confirm no recent defaults"
        ]
    }

    result = explainer.explain(
        decision="Loan approved",
        input_data={"credit_score": 750},
        output_data={"confidence": 0.92},
        metadata=metadata
    )

    assert result.decision == "Loan approved"
    assert result.explanation_type == ExplanationType.CHAIN_OF_THOUGHT
    assert len(result.evidence) == 3  # 3 reasoning steps

    # Check evidence preserves step order
    assert "Step 1" in result.evidence[0].description
    assert "Step 2" in result.evidence[1].description
    assert "Step 3" in result.evidence[2].description


def test_chain_of_thought_explainer_no_steps():
    """Test chain-of-thought explanation without reasoning steps."""
    explainer = ChainOfThoughtExplainer()

    result = explainer.explain(
        decision="Decision",
        input_data={},
        output_data={"confidence": 0.8},
        metadata={}
    )

    # Should indicate no steps available
    assert "No reasoning" in result.reasoning or "not provided" in result.reasoning.lower()
    assert len(result.evidence) == 0


def test_chain_of_thought_explainer_step_numbering():
    """Test that steps are numbered correctly in evidence."""
    explainer = ChainOfThoughtExplainer()

    metadata = {
        "reasoning_steps": [
            "Check A",
            "Check B",
            "Check C"
        ]
    }

    result = explainer.explain(
        decision="Decision",
        input_data={},
        output_data={"confidence": 0.8},
        metadata=metadata
    )

    # Evidence features should be "step_1", "step_2", "step_3"
    features = [e.feature for e in result.evidence]
    assert "step_1" in features
    assert "step_2" in features
    assert "step_3" in features


# ============================================================================
# RuleBasedExplainer Tests
# ============================================================================


def test_rule_based_explainer_with_rules():
    """Test rule-based explanation with rules."""
    explainer = RuleBasedExplainer()

    metadata = {
        "rules": [
            "IF credit_score >= 700 THEN eligible",
            "IF income >= 50000 THEN sufficient"
        ]
    }

    result = explainer.explain(
        decision="Approved",
        input_data={"credit_score": 750, "income": 80000},
        output_data={"confidence": 0.95},
        metadata=metadata
    )

    assert result.decision == "Approved"
    assert result.explanation_type == ExplanationType.RULE_BASED
    assert len(result.evidence) == 2  # 2 rules

    # Check evidence contains rule text
    evidence_text = " ".join([e.description for e in result.evidence])
    assert "credit_score >= 700" in evidence_text
    assert "income >= 50000" in evidence_text


def test_rule_based_explainer_no_rules():
    """Test rule-based explanation without rules."""
    explainer = RuleBasedExplainer()

    result = explainer.explain(
        decision="Decision",
        input_data={},
        output_data={"confidence": 0.8},
        metadata={}
    )

    # Should indicate no rules available
    assert "No rules" in result.reasoning or "not provided" in result.reasoning.lower()
    assert len(result.evidence) == 0


def test_rule_based_explainer_rule_confidence():
    """Test that rules get appropriate importance scores."""
    explainer = RuleBasedExplainer()

    metadata = {
        "rules": [
            "Rule 1",
            "Rule 2"
        ]
    }

    result = explainer.explain(
        decision="Decision",
        input_data={},
        output_data={"confidence": 0.9},
        metadata=metadata
    )

    # All rules should have importance of 1.0 (deterministic rules)
    for evidence in result.evidence:
        assert evidence.importance == 1.0


# ============================================================================
# Factory Function Tests
# ============================================================================


def test_create_explainer_feature_importance():
    """Test creating FeatureImportanceExplainer via factory."""
    explainer = create_explainer(ExplanationType.FEATURE_IMPORTANCE)
    assert isinstance(explainer, FeatureImportanceExplainer)


def test_create_explainer_counterfactual():
    """Test creating CounterfactualExplainer via factory."""
    explainer = create_explainer(ExplanationType.COUNTERFACTUAL)
    assert isinstance(explainer, CounterfactualExplainer)


def test_create_explainer_example_based():
    """Test creating ExampleBasedExplainer via factory."""
    explainer = create_explainer(ExplanationType.EXAMPLE_BASED)
    assert isinstance(explainer, ExampleBasedExplainer)


def test_create_explainer_chain_of_thought():
    """Test creating ChainOfThoughtExplainer via factory."""
    explainer = create_explainer(ExplanationType.CHAIN_OF_THOUGHT)
    assert isinstance(explainer, ChainOfThoughtExplainer)


def test_create_explainer_rule_based():
    """Test creating RuleBasedExplainer via factory."""
    explainer = create_explainer(ExplanationType.RULE_BASED)
    assert isinstance(explainer, RuleBasedExplainer)


def test_create_explainer_invalid_type():
    """Test creating explainer with invalid type raises KeyError."""
    with pytest.raises(KeyError):
        create_explainer("invalid_type")


# ============================================================================
# Convenience Function Tests
# ============================================================================


def test_explain_agent_decision_basic():
    """Test explain_agent_decision convenience function."""
    result = explain_agent_decision(
        decision="Loan approved",
        input_data={"credit_score": 750},
        output_data={"confidence": 0.9},
        explanation_type=ExplanationType.FEATURE_IMPORTANCE
    )

    assert result.decision == "Loan approved"
    assert result.explanation_type == ExplanationType.FEATURE_IMPORTANCE
    assert result.confidence == 0.9


def test_explain_agent_decision_with_metadata():
    """Test explain_agent_decision with metadata."""
    result = explain_agent_decision(
        decision="Decision",
        input_data={},
        output_data={"confidence": 0.8},
        explanation_type=ExplanationType.RULE_BASED,
        metadata={"rules": ["IF x THEN y"]}
    )

    assert result.explanation_type == ExplanationType.RULE_BASED
    assert len(result.evidence) == 1


def test_explain_agent_decision_all_types():
    """Test explain_agent_decision works with all explainer types."""
    types_to_test = [
        ExplanationType.FEATURE_IMPORTANCE,
        ExplanationType.COUNTERFACTUAL,
        ExplanationType.EXAMPLE_BASED,
        ExplanationType.CHAIN_OF_THOUGHT,
        ExplanationType.RULE_BASED,
    ]

    for exp_type in types_to_test:
        result = explain_agent_decision(
            decision="Test decision",
            input_data={"feature": 100},
            output_data={"confidence": 0.8},
            explanation_type=exp_type,
            metadata={}
        )

        assert result.explanation_type == exp_type
        assert result.decision == "Test decision"


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow_feature_importance():
    """Test complete workflow with feature importance."""
    # 1. Create explainer
    explainer = create_explainer(ExplanationType.FEATURE_IMPORTANCE)

    # 2. Generate explanation
    result = explainer.explain(
        decision="Loan approved",
        input_data={"credit_score": 750, "income": 80000, "age": 35},
        output_data={"confidence": 0.92}
    )

    # 3. Convert to different formats
    human = result.to_human_readable()
    json_output = result.to_json()
    markdown = result.to_markdown()

    # 4. Verify all formats contain key information
    assert "Loan approved" in human
    assert "Loan approved" in markdown

    parsed_json = json.loads(json_output)
    assert parsed_json["decision"] == "Loan approved"
    assert len(parsed_json["evidence"]) == 3


def test_full_workflow_counterfactual():
    """Test complete workflow with counterfactual explanation."""
    result = explain_agent_decision(
        decision="Approved",
        input_data={"score": 800},
        output_data={"confidence": 0.95},
        explanation_type=ExplanationType.COUNTERFACTUAL,
        metadata={"threshold": 700}
    )

    # Verify counterfactuals were generated
    assert len(result.counterfactuals) > 0

    # Verify output formats work
    human = result.to_human_readable()
    assert "Approved" in human

    markdown = result.to_markdown()
    assert "Approved" in markdown


def test_multiple_explainers_same_decision():
    """Test explaining same decision with different explainer types."""
    decision = "Loan approved"
    input_data = {"credit_score": 750, "income": 80000}
    output_data = {"confidence": 0.92}

    # Explain using feature importance
    fi_result = explain_agent_decision(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        explanation_type=ExplanationType.FEATURE_IMPORTANCE
    )

    # Explain using counterfactual
    cf_result = explain_agent_decision(
        decision=decision,
        input_data=input_data,
        output_data=output_data,
        explanation_type=ExplanationType.COUNTERFACTUAL,
        metadata={"threshold": 700}
    )

    # Both should explain same decision
    assert fi_result.decision == cf_result.decision
    assert fi_result.confidence == cf_result.confidence

    # But use different explanation types
    assert fi_result.explanation_type != cf_result.explanation_type

    # And have different evidence/reasoning
    assert fi_result.reasoning != cf_result.reasoning
