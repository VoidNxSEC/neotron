"""
Document Ingestion Agent
Specialized agent for analyzing and structuring compliance documents.
"""

import logging
from typing import Any

from neutron.agents.cortex import Agent

logger = logging.getLogger("neutron.agents.document")


class DocumentIngestionAgent(Agent):
    """
    Agent specialized in ingesting and analyzing regulatory documents.
    """

    def __init__(self, name: str, role: str = "compliance_librarian"):
        super().__init__(name=name, role=role)
        self.system_prompt = (
            f"You are {name}, an expert in regulatory compliance and document analysis. "
            "Your goal is to extract key requirements, risk levels, and action items from documents. "
            "Always output strict JSON."
        )

    def build_prompt(self, task: dict[str, Any]) -> str:
        """Construct a prompt specialized for document analysis."""
        data = task.get("data", {})
        doc_content = data.get("text", "")
        filename = data.get("filename", "unknown")

        # Simple truncation strategy for MVP
        # In production, this would use chunking/embedding
        truncated_content = doc_content[:15000]
        if len(doc_content) > 15000:
            truncated_content += "\n...[TRUNCATED]..."

        return f"""
        Task: Analyze the following compliance document.
        Filename: {filename}
        
        --- DOCUMENT START ---
        {truncated_content}
        --- DOCUMENT END ---
        
        Required Analysis:
        1. Summarize the core purpose of the document.
        2. Identify specific compliance obligations (MUST/SHALL).
        3. Assess the overall risk level if non-compliant.
        4. List immediate action items for the engineering team.
        
        Output Format (JSON):
        {{
            "summary": "Brief summary...",
            "obligations": ["obligation 1", "obligation 2"],
            "risk_level": "High|Medium|Low",
            "risk_reasoning": "Why this risk level...",
            "action_items": ["action 1", "action 2"],
            "tags": ["tag1", "tag2"]
        }}
        """
