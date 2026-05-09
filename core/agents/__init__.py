"""NZ Legal RAG — Multi-Agent Pipeline

Full pipeline: Intake → Analyst → (parallel) Auditor + Strategist → Synthesis
"""

from core.agents.intake_agent import CaseIntakeAgent, IntakeResult
from core.agents.defence_analyst import DefenceAnalyst
from core.agents.citation_auditor import CitationAuditor, AuditResult
from core.agents.defence_strategist import DefenceStrategist, StrategyResult
from core.agents.synthesis_agent import SynthesisAgent, SynthesisResult

__all__ = [
    "CaseIntakeAgent", "IntakeResult",
    "DefenceAnalyst",
    "CitationAuditor", "AuditResult",
    "DefenceStrategist", "StrategyResult",
    "SynthesisAgent", "SynthesisResult",
]
