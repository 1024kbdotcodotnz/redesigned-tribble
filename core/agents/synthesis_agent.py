#!/usr/bin/env python3
"""
Synthesis Agent

Assembles outputs from all upstream agents into a cohesive, formatted final response
suitable for both human reading and PDF export.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class SynthesisResult:
    """Final structured output."""
    formatted_answer: str = ""
    executive_summary: str = ""
    confidence_breakdown: str = ""
    citation_warnings: str = ""
    strategic_appendix: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class SynthesisAgent:
    """
    Final agent in the pipeline.

    Responsibilities:
    1. Merge the Defence Analyst's legal reasoning with auditor warnings.
    2. Append the Strategist's tactical recommendations.
    3. Generate an executive summary and confidence breakdown.
    4. Format everything for clean PDF rendering (minimal markdown, clear headings).
    """

    def __init__(self, llm: Optional[Any] = None):
        self.llm = llm  # Optional — can run deterministically without LLM

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(self,
                   analysis_text: str,
                   audit: Any,
                   strategy: Any,
                   intake: Any,
                   confidence: float,
                   sources: List[Any]) -> SynthesisResult:
        """Assemble all agent outputs into the final response."""

        # Use auditor's corrected response if available and there are unverified citations
        corrected = getattr(audit, "corrected_response", None) if audit else None
        base_text = corrected if corrected else analysis_text

        # Build citation warnings section
        citation_warnings = self._build_citation_warnings(audit)

        # Build strategic appendix
        strategic_appendix = self._build_strategic_appendix(strategy)

        # Build confidence breakdown
        confidence_breakdown = self._build_confidence_breakdown(confidence, intake, audit)

        # Build executive summary
        executive_summary = self._build_executive_summary(base_text, strategy, confidence)

        # Assemble final formatted answer
        formatted_answer = self._assemble_final_answer(
            base_text, citation_warnings, strategic_appendix
        )

        return SynthesisResult(
            formatted_answer=formatted_answer,
            executive_summary=executive_summary,
            confidence_breakdown=confidence_breakdown,
            citation_warnings=citation_warnings,
            strategic_appendix=strategic_appendix,
            metadata={
                "hallucination_risk": getattr(audit, "hallucination_risk", 0.0),
                "unverified_citations": getattr(audit, "unverified_citations", []),
                "tactical_priority_count": len(getattr(strategy, "tactical_priorities", [])),
            }
        )

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_citation_warnings(self, audit: Any) -> str:
        """Format auditor findings into a concise warning block."""
        if not audit:
            return ""

        unverified = getattr(audit, "unverified_citations", [])
        risk = getattr(audit, "hallucination_risk", 0.0)
        report = getattr(audit, "audit_report", "")

        if not unverified and risk < 0.3:
            return "✅ All citations verified against retrieved sources."

        lines = ["⚠️  CITATION AUDIT WARNINGS", "-" * 40]
        if unverified:
            lines.append(f"Unverified citations ({len(unverified)}):")
            for c in unverified[:5]:
                lines.append(f"  • {c}")
            if len(unverified) > 5:
                lines.append(f"  ... and {len(unverified) - 5} more")
        if risk >= 0.5:
            lines.append(f"\nHigh hallucination risk detected ({risk:.0%}).")
            lines.append("Independent verification of ALL citations is strongly recommended before use in proceedings.")
        elif report:
            lines.append(f"\n{report}")

        return "\n".join(lines)

    def _build_strategic_appendix(self, strategy: Any) -> str:
        """Format strategist output into a clean appendix."""
        if not strategy:
            return ""

        motions = getattr(strategy, "procedural_motions", [])
        cross = getattr(strategy, "cross_examination_angles", [])
        plea = getattr(strategy, "plea_considerations", "")
        priorities = getattr(strategy, "tactical_priorities", [])
        risks = getattr(strategy, "risk_flags", [])

        if not any([motions, cross, plea, priorities, risks]):
            return ""

        lines = ["\n📋 DEFENCE STRATEGY & TACTICS", "=" * 40]

        if priorities:
            lines.append("\n🎯 Tactical Priorities")
            for i, p in enumerate(priorities, 1):
                lines.append(f"  {i}. {p}")

        if motions:
            lines.append("\n📑 Procedural Motions / Applications")
            for m in motions:
                lines.append(f"  • {m}")

        if cross:
            lines.append("\n🔍 Cross-Examination Angles")
            for c in cross:
                lines.append(f"  • {c}")

        if plea:
            lines.append(f"\n⚖️  Plea Considerations")
            lines.append(f"  {plea}")

        if risks:
            lines.append("\n🚩 Risk Flags")
            for r in risks:
                lines.append(f"  • {r}")

        return "\n".join(lines)

    def _build_confidence_breakdown(self, confidence: float, intake: Any, audit: Any) -> str:
        """Explain how the confidence score was derived."""
        parts = [f"Overall Confidence: {confidence:.0%}"]

        if intake:
            ic = getattr(intake, "confidence", 1.0)
            if ic < 0.8:
                parts.append(f"• Intake classification confidence: {ic:.0%} (lowered final score)")

        if audit:
            risk = getattr(audit, "hallucination_risk", 0.0)
            if risk > 0:
                parts.append(f"• Citation hallucination risk: {risk:.0%}")
            uv = len(getattr(audit, "unverified_citations", []))
            if uv:
                parts.append(f"• Unverified citations: {uv}")

        return "\n".join(parts)

    def _build_executive_summary(self, analysis: str, strategy: Any, confidence: float) -> str:
        """Generate a 2–3 sentence TL;DR."""
        strat_summary = getattr(strategy, "executive_summary", "") if strategy else ""

        if strat_summary:
            return f"Confidence: {confidence:.0%}. {strat_summary}"

        # Fallback: extract first sentence of analysis
        first_sent = analysis.split(".")[0] + "." if "." in analysis else analysis[:200]
        return f"Confidence: {confidence:.0%}. {first_sent}"

    def _assemble_final_answer(self, analysis: str, citation_warnings: str, strategic_appendix: str) -> str:
        """Combine all sections into the final text."""
        parts = [analysis.strip()]

        if citation_warnings:
            parts.append("\n\n" + citation_warnings)

        if strategic_appendix:
            parts.append("\n" + strategic_appendix)

        return "\n\n".join(parts)
