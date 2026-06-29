#!/usr/bin/env python3
"""NZ Legal RAG — Core Package"""

from core.agent_swarm import AgentSwarm, OllamaLLMClient, SynthesizedReport
from core.parser import DisclosureParser, ParsedDisclosure
from core.rag_integration import SwarmEnabledRAG, create_swarm_rag

__all__ = [
    "AgentSwarm",
    "OllamaLLMClient",
    "SynthesizedReport",
    "DisclosureParser",
    "ParsedDisclosure",
    "SwarmEnabledRAG",
    "create_swarm_rag",
]
