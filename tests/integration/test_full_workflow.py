"""
Integration Tests - Full NEXUS Workflow

End-to-end tests validating complete platform integration:
- CORTEX (Multi-Agent) + SYNAPSE (Memory) + GDPR + ORACLE + EU AI Act
"""

import asyncio
from typing import Any

import pytest
from neutron.orchestration.cortex import (
    AgentResult,
    AgentSwarm,
    ConsensusStrategy,
    Task,
)

from neutron.compliance.sentinel import AgentOutput
from neutron.reasoning import ExplanationType

# =============================================================================
# Mock Components
# =============================================================================


class MockAgent:
    """Mock agent for integration testing"""

    def __init__(self, agent_id: str, output: Any, confidence: float):
        self.agent_id = agent_id
        self._output = output
        self._confidence = confidence

    async def execute(self, task: Task) -> AgentResult:
        """Execute task"""
        await asyncio.sleep(0.01)  # Simulate processing
        return AgentResult(
            agent_id=self.agent_id,
            output=self._output,
            confidence=self._confidence,
            explanation=f"{self.agent_id} analysis complete",
        )


# =============================================================================
# Integration Tests
# =============================================================================


class TestFullWorkflowIntegration:
    """Integration tests for complete NEXUS workflow"""

    @pytest.mark.asyncio
    async def test_cortex_oracle_integration(self):
        """Test CORTEX multi-agent with ORACLE explanation"""
        # Create agent swarm
        agents = [
            MockAgent("credit_model_a", "approved", 0.92),
            MockAgent("credit_model_b", "approved", 0.88),
            MockAgent("risk_model", "approved", 0.85),
        ]

        swarm = AgentSwarm(agents, name="credit_assessment")

        # Create task
        task = Task(
            type="loan_decision",
            input={"credit_score": 750, "income": 85000},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        # Execute with explanation
        result = await swarm.execute(
            task, generate_explanation=True, explanation_type=ExplanationType.CHAIN_OF_THOUGHT
        )

        # Validate consensus
        assert result.consensus_output == "approved"
        assert result.consensus_confidence > 0.8
        assert result.agreement_score > 0.5

        # Validate explanation
        assert result.explanation is not None
        assert result.explanation.explanation_type == ExplanationType.CHAIN_OF_THOUGHT
        assert result.explanation.confidence == result.consensus_confidence
        assert len(result.explanation.evidence) >= 3  # Should have reasoning steps

        # Validate human-readable output
        human_readable = result.explanation.to_human_readable()
        assert "approved" in human_readable.lower()
        assert "step" in human_readable.lower()

    @pytest.mark.asyncio
    async def test_multiple_explanation_types(self):
        """Test generating different explanation types for same decision"""
        agents = [
            MockAgent("agent_1", "positive", 0.9),
            MockAgent("agent_2", "positive", 0.85),
        ]

        swarm = AgentSwarm(agents)
        task = Task(
            type="sentiment_analysis",
            input={"text": "Great product!"},
            consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE,
        )

        # Test all explanation types
        explanation_types = [
            ExplanationType.FEATURE_IMPORTANCE,
            ExplanationType.CHAIN_OF_THOUGHT,
            ExplanationType.EXAMPLE_BASED,
        ]

        for exp_type in explanation_types:
            result = await swarm.execute(task, generate_explanation=True, explanation_type=exp_type)

            assert result.explanation is not None
            assert result.explanation.explanation_type == exp_type
            assert result.explanation.decision == f"Swarm consensus: {result.consensus_output}"

    @pytest.mark.asyncio
    async def test_compliance_validation_integration(self):
        """Test that compliance validation works in workflow"""
        from neutron.compliance.auditors.ai_act import (
            AISystemRiskLevel,
            classify_ai_system_risk,
            validate_ai_act_compliance,
        )

        # Create output for high-risk AI system
        output = AgentOutput(
            content="Loan approved",
            metadata={
                "use_case": "loan_approval",
                "ai_disclosure": True,
                "system_info": "NEXUS Credit Assessment System",
                "capabilities": "Analyzes creditworthiness using ML models",
                "limitations": "Does not account for recent life events",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_in_the_loop",
                "overseer_id": "loan_officer_123",
                "can_override": True,
            },
        )

        # Validate risk classification
        risk = classify_ai_system_risk("loan_approval")
        assert risk == AISystemRiskLevel.HIGH

        # Validate AI Act compliance
        results = validate_ai_act_compliance(output)
        assert len(results) == 3  # Article 5, 13, 14

        # All should pass
        assert all(r.passed for r in results)

    @pytest.mark.asyncio
    async def test_end_to_end_transparent_decision(self):
        """Test complete transparent decision-making workflow"""
        # 1. Multi-agent consensus
        agents = [
            MockAgent("model_1", "high_risk", 0.88),
            MockAgent("model_2", "high_risk", 0.92),
            MockAgent("model_3", "medium_risk", 0.75),
        ]

        swarm = AgentSwarm(agents, name="risk_assessment")

        task = Task(
            type="fraud_detection",
            input={"transaction_id": "TXN-12345", "amount": 10000},
            consensus_strategy=ConsensusStrategy.MAJORITY_VOTE,
        )

        # 2. Execute with explanation
        result = await swarm.execute(
            task, generate_explanation=True, explanation_type=ExplanationType.CHAIN_OF_THOUGHT
        )

        # 3. Validate consensus reached
        assert result.consensus_output in ["high_risk", "medium_risk"]
        assert result.num_agents == 3

        # 4. Validate explanation generated
        assert result.explanation is not None
        explanation_text = result.explanation.to_human_readable()

        # Should include all agents in chain of thought
        assert "model_1" in explanation_text or "agent" in explanation_text.lower()

        # 5. Validate explanation can be exported in multiple formats
        json_export = result.explanation.to_json()
        markdown_export = result.explanation.to_markdown()

        assert "high_risk" in json_export
        assert "high_risk" in markdown_export

        # 6. Create compliance output
        compliance_output = AgentOutput(
            content=result.consensus_output,
            metadata={
                "use_case": "fraud_detection",
                "ai_disclosure": True,
                "system_info": "NEXUS Fraud Detection System",
                "capabilities": "Real-time transaction risk assessment",
                "limitations": "Cannot detect novel fraud patterns",
                "human_oversight_enabled": True,
                "oversight_mechanism": "human_on_the_loop",
                "overseer_id": "fraud_analyst_456",
                "can_override": True,
            },
        )

        # 7. Validate EU AI Act compliance
        from neutron.compliance.auditors.ai_act import validate_ai_act_compliance

        ai_act_results = validate_ai_act_compliance(compliance_output)
        assert all(r.passed for r in ai_act_results)

        # 8. Complete workflow validated
        assert True  # All steps passed


class TestComplianceIntegration:
    """Integration tests for compliance frameworks"""

    def test_lgpd_gdpr_ai_act_interoperability(self):
        """Test that all three compliance frameworks work together"""
        from neutron.compliance.auditors import (
            validate_ai_act_compliance,
            validate_with_gdpr,
            validate_with_lgpd,
        )

        # Create output that should pass all three frameworks
        output = AgentOutput(
            content="Customer data exported",
            has_explanation=True,
            explanation="Data exported per Article 18 request with full audit trail",
            explanation_quality=0.85,
            metadata={
                # LGPD
                "exportable_format": "json",
                "data_structure": {"customer": "object", "records": "list"},
                # GDPR
                "risk_level": "low",
                "data_access_enabled": True,
                "data_categories": ["personal", "financial"],
                "retention_period": "90 days",
                "export_format": "JSON",
                "processes_personal_data": True,
                "erasure_supported": True,
                "erasure_endpoint": "/api/v1/customers/{id}/delete",
                # EU AI Act
                "use_case": "data_export",
                "ai_disclosure": True,
                "system_info": "NEXUS Data Export System",
            },
        )

        # Validate all frameworks
        lgpd_results = validate_with_lgpd(output)
        gdpr_results = validate_with_gdpr(output)
        ai_act_results = validate_ai_act_compliance(output)

        # All should have some passing validations
        assert len(lgpd_results) > 0
        assert len(gdpr_results) > 0
        assert len(ai_act_results) > 0

        # At least some from each should pass
        assert any(r.passed for r in lgpd_results)
        assert any(r.passed for r in gdpr_results)
        assert any(r.passed for r in ai_act_results)


class TestExplainabilityIntegration:
    """Integration tests for explainability across components"""

    @pytest.mark.asyncio
    async def test_explanation_with_different_consensus_strategies(self):
        """Test explanations work with all consensus strategies"""
        agents = [
            MockAgent("agent_1", 0.8, 0.9),
            MockAgent("agent_2", 0.75, 0.85),
            MockAgent("agent_3", 0.82, 0.88),
        ]

        strategies = [
            ConsensusStrategy.MAJORITY_VOTE,
            ConsensusStrategy.WEIGHTED_AVERAGE,
            ConsensusStrategy.BEST_CONFIDENCE,
        ]

        for strategy in strategies:
            swarm = AgentSwarm(agents)
            task = Task(
                type="prediction",
                input={"data": "test"},
                consensus_strategy=strategy,
            )

            result = await swarm.execute(
                task, generate_explanation=True, explanation_type=ExplanationType.FEATURE_IMPORTANCE
            )

            assert result.explanation is not None
            assert strategy.value in result.explanation.to_human_readable().lower()

    def test_explanation_formats_are_consistent(self):
        """Test that all explanation formats contain same core information"""
        from neutron.reasoning import ExplanationType, explain_agent_decision

        decision = "approved"
        input_data = {"score": 750}
        output_data = {"confidence": 0.92}

        explanation = explain_agent_decision(
            decision=decision,
            input_data=input_data,
            output_data=output_data,
            explanation_type=ExplanationType.FEATURE_IMPORTANCE,
        )

        # Get all formats
        human = explanation.to_human_readable()
        json_str = explanation.to_json()
        markdown = explanation.to_markdown()

        # All should contain decision
        assert "approved" in human.lower()
        assert "approved" in json_str.lower()
        assert "approved" in markdown.lower()

        # All should contain confidence
        assert "92" in human or "0.92" in human
        assert "0.92" in json_str
        assert "92" in markdown or "0.92" in markdown


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformanceIntegration:
    """Performance and scalability integration tests"""

    @pytest.mark.asyncio
    async def test_multi_agent_performance(self):
        """Test performance with multiple agents"""
        # Create large swarm
        agents = [MockAgent(f"agent_{i}", "result", 0.8 + (i * 0.01)) for i in range(10)]

        swarm = AgentSwarm(agents)
        task = Task(
            type="analysis",
            input={"data": "test"},
            consensus_strategy=ConsensusStrategy.WEIGHTED_AVERAGE,
        )

        import time

        start = time.time()

        result = await swarm.execute(
            task, generate_explanation=True, explanation_type=ExplanationType.CHAIN_OF_THOUGHT
        )

        duration = time.time() - start

        # Should complete in reasonable time (< 1 second for 10 agents)
        assert duration < 1.0

        # All agents should have participated
        assert result.num_agents == 10

        # Explanation should be generated
        assert result.explanation is not None

    @pytest.mark.asyncio
    async def test_explanation_generation_performance(self):
        """Test explanation generation doesn't add significant overhead"""
        agents = [MockAgent(f"agent_{i}", "test", 0.9) for i in range(5)]
        swarm = AgentSwarm(agents)
        task = Task(type="test", input={}, consensus_strategy=ConsensusStrategy.MAJORITY_VOTE)

        import time

        # Without explanation
        start = time.time()
        result_no_exp = await swarm.execute(task, generate_explanation=False)
        time_no_exp = time.time() - start

        # With explanation
        start = time.time()
        result_with_exp = await swarm.execute(
            task, generate_explanation=True, explanation_type=ExplanationType.FEATURE_IMPORTANCE
        )
        time_with_exp = time.time() - start

        # Explanation overhead should be minimal (< 100ms for 5 agents)
        overhead = time_with_exp - time_no_exp
        assert overhead < 0.1  # Less than 100ms overhead

        # Results should be equivalent
        assert result_no_exp.consensus_output == result_with_exp.consensus_output
