#!/usr/bin/env python3
"""
RAG Integration — Wires full agent swarm into existing NZLegalRAG engine.
Production v2 with real LLM calls and structured report output.
"""

from typing import Any, Dict, List, Optional
from core.agent_swarm import AgentSwarm, OllamaLLMClient


class SwarmEnabledRAG:
    """Wraps base RAG engine with multi-agent disclosure analysis."""

    def __init__(self, base_rag_engine: Any):
        self.rag = base_rag_engine
        # Use the same model as the base engine, fallback to qwen2.5:14b
        model = getattr(base_rag_engine, 'llm_model', 'qwen2.5:14b')
        llm = OllamaLLMClient(model=model)
        self.swarm = AgentSwarm(llm_client=llm, rag_engine=base_rag_engine)

    def analyse_disclosure(self, raw_text: str, extra_collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run full 6-agent pipeline on disclosure text.

        Args:
            raw_text: Disclosure text to analyse.
            extra_collections: Optional list of collection names (e.g. uploaded
                documents) to include in RAG retrieval.

        Returns dict with all report fields for API serialization.
        """
        return self.swarm.analyse_disclosure(raw_text, extra_collections=extra_collections)

    def analyse(self, raw_text: str, extra_collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Alias for analyse_disclosure."""
        return self.analyse_disclosure(raw_text, extra_collections=extra_collections)


def create_swarm_rag(base_rag_engine: Any) -> SwarmEnabledRAG:
    """Factory function to create swarm-enabled RAG wrapper."""
    return SwarmEnabledRAG(base_rag_engine)
