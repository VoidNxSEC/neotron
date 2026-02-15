"""
ORACLE Explainability API Endpoints

Exposes the ORACLE explainability framework via REST API,
allowing direct access to decision explanations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("neutron.api.oracle")

router = APIRouter(prefix="/v1/oracle", tags=["oracle"])


class OracleExplainRequest(BaseModel):
    """Request for an ORACLE explanation."""

    decision: str = Field(..., description="The decision to explain (e.g., 'approved', 'rejected')")
    input_data: Dict[str, Any] = Field(default_factory=dict, description="Input data that led to the decision")
    output_data: Dict[str, Any] = Field(default_factory=dict, description="Output/result data from the decision")
    explanation_type: str = Field(
        default="feature_importance",
        description="Type of explanation: feature_importance, counterfactual, chain_of_thought, rule_based, example_based",
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata for explainers")


class OracleExplainResponse(BaseModel):
    """Response containing an ORACLE explanation."""

    decision: str
    explanation_type: str
    confidence: float
    evidence: list[Dict[str, Any]]
    reasoning: str
    counterfactuals: list[Dict[str, Any]] = []
    human_readable: str
    markdown: str


@router.post("/explain", response_model=OracleExplainResponse)
async def explain_decision(request: OracleExplainRequest) -> OracleExplainResponse:
    """
    Generate an explanation for an AI decision using the ORACLE framework.

    Supports multiple explanation types:
    - **feature_importance**: Ranks input features by influence on the decision
    - **counterfactual**: Shows "what if" scenarios
    - **chain_of_thought**: Step-by-step reasoning trace
    - **rule_based**: Maps to deterministic rules
    - **example_based**: References similar past cases
    """
    from neutron.reasoning.oracle import ExplanationType, explain_agent_decision

    type_map = {
        "feature_importance": ExplanationType.FEATURE_IMPORTANCE,
        "counterfactual": ExplanationType.COUNTERFACTUAL,
        "chain_of_thought": ExplanationType.CHAIN_OF_THOUGHT,
        "rule_based": ExplanationType.RULE_BASED,
        "example_based": ExplanationType.EXAMPLE_BASED,
    }

    explanation_type = type_map.get(request.explanation_type)
    if explanation_type is None:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid explanation_type '{request.explanation_type}'. Valid: {sorted(type_map.keys())}",
        )

    try:
        result = explain_agent_decision(
            decision=request.decision,
            input_data=request.input_data,
            output_data=request.output_data,
            explanation_type=explanation_type,
            metadata=request.metadata,
        )

        return OracleExplainResponse(
            decision=result.decision,
            explanation_type=result.explanation_type.value,
            confidence=result.confidence,
            evidence=[
                {
                    "feature": e.feature,
                    "value": e.value,
                    "importance": e.importance,
                    "description": e.description,
                }
                for e in result.evidence
            ],
            reasoning=result.reasoning,
            counterfactuals=result.counterfactuals,
            human_readable=result.to_human_readable(),
            markdown=result.to_markdown(),
        )
    except Exception as e:
        logger.error(f"ORACLE explanation error: {e}")
        raise HTTPException(status_code=500, detail=f"Explanation generation failed: {str(e)}")
