#!/usr/bin/env python3
"""
Defence Strategy Agent

Generates tactical recommendations based on the legal analysis.
Operates exclusively from a defence-counsel perspective.
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class StrategyResult:
    """Structured tactical output from the Defence Strategist."""
    procedural_motions: List[str] = field(default_factory=list)
    cross_examination_angles: List[str] = field(default_factory=list)
    plea_considerations: str = ""
    tactical_priorities: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    executive_summary: str = ""


class DefenceStrategist:
    """
    Final reasoning agent before synthesis.

    Responsibilities:
    1. Translate legal weaknesses into actionable procedural motions.
    2. Identify cross-examination angles from inconsistencies.
    3. Assess plea strategy (trial vs early resolution).
    4. Rank tactical priorities by impact and feasibility.
    5. Flag risks that could backfire on the defence.
    """

    def __init__(self, llm: Any):
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def strategize(self, analysis_text: str, intake: Any, sources: List[Any]) -> StrategyResult:
        """Generate defence strategy from analysis output."""
        if not self.llm:
            return StrategyResult(executive_summary="[LLM not configured — skipping strategy]")

        entities = getattr(intake, "key_entities", {}) if intake else {}
        analysis_type = getattr(intake, "detected_analysis_type", "general") if intake else "general"

        prompt = self._build_strategy_prompt(analysis_text, entities, analysis_type)

        try:
            raw = self.llm.invoke(prompt)
        except Exception as e:
            return StrategyResult(executive_summary=f"[Strategy Agent error: {e}]")

        parsed = self._parse_json_response(raw)
        if not parsed:
            return StrategyResult(executive_summary="[Strategy Agent returned unparsable output]")

        return self._hydrate_result(parsed)

    # ------------------------------------------------------------------
    # Prompt engineering
    # ------------------------------------------------------------------

    def _build_strategy_prompt(self, analysis: str, entities: Dict, analysis_type: str) -> str:
        case_names = ", ".join(entities.get("case_names", [])) or "Not specified"
        charges = ", ".join(entities.get("charges", [])) or "Not specified"
        statutes = ", ".join(entities.get("statutes", [])) or "Not specified"

        return f"""You are a senior New Zealand Defence Counsel's tactical advisor.
Your job is to read the legal analysis below and produce actionable strategy.

CONTEXT:
- Analysis Type: {analysis_type}
- Case / Accused: {case_names}
- Charges: {charges}
- Statutes Mentioned: {statutes}

RULES:
1. procedural_motions: List specific motions or applications the defence should file (e.g., "Application to exclude evidence under s 21 NZBORA", "Abuse of process stay application").
2. cross_examination_angles: Identify witness credibility attacks, inconsistency lines, or factual challenges.
3. plea_considerations: Briefly advise on whether to plead not guilty, seek a discharge, or negotiate — based ONLY on weaknesses identified.
4. tactical_priorities: Rank the top 3–5 actions by impact (highest first).
5. risk_flags: Warn about anything that could backfire (e.g., "Opening the door on bad character", "Challenging DNA may trigger re-testing").
6. executive_summary: One paragraph summarising the overall tactical position.
7. Respond ONLY with valid JSON. No markdown fences, no explanation, no <think> tags.

LEGAL ANALYSIS:
{analysis}

RESPOND WITH EXACTLY THIS JSON SCHEMA:
{{
  "procedural_motions": ["..."],
  "cross_examination_angles": ["..."],
  "plea_considerations": "...",
  "tactical_priorities": ["..."],
  "risk_flags": ["..."],
  "executive_summary": "..."
}}
"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict]:
        if not text:
            return None
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        else:
            brace = re.search(r"\{.*\}", text, re.DOTALL)
            if brace:
                text = brace.group(0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _hydrate_result(self, parsed: Dict) -> StrategyResult:
        return StrategyResult(
            procedural_motions=parsed.get("procedural_motions", []),
            cross_examination_angles=parsed.get("cross_examination_angles", []),
            plea_considerations=parsed.get("plea_considerations", ""),
            tactical_priorities=parsed.get("tactical_priorities", []),
            risk_flags=parsed.get("risk_flags", []),
            executive_summary=parsed.get("executive_summary", "")
        )
