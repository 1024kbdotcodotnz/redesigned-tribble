import os
from pathlib import Path
from typing import Any, Dict

import pytest

from core.agent_swarm import AgentSwarm

LIM_DIR = Path(os.environ.get("DISCLOSURE_LIM_DIR", Path(__file__).parent / "data" / "lim"))
TEST_FILES = [
    LIM_DIR / "Scanned_v2.txt",
    LIM_DIR / "scanned_document.txt",
    LIM_DIR / "adf_scan_ocr_20260323_105350.txt",
]

_MISSING_FILES = [str(f) for f in TEST_FILES if not f.exists()]


class TheoryAwareFakeLLM:
    """Deterministic LLM stand-in that echoes the case theory only when prompted."""

    def __init__(self) -> None:
        self.calls: list[Dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> str:
        self.calls.append({"method": "generate", "prompt": prompt, "system": system})
        if "CASE THEORY" in prompt or "## CASE THEORY" in prompt:
            return """
This analysis is anchored to the case theory: the warrantless search under s 20
and the unsigned admission undermine the Crown case. A s 30 exclusion
application should be considered.
"""
        return "Generic analysis without case-specific statutory references."

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        self.calls.append({"method": "generate_json", "prompt": prompt, "system": system})
        return {
            "central_theory": "The warrantless search under s 20 and the unsigned admission undermine the Crown case.",
            "issues": [
                {
                    "rank": 1,
                    "name": "Warrantless search under s 20",
                    "legal_basis": ["s 20 Misuse of Drugs Act 1975", "s 21 NZBORA"],
                    "supporting_facts": ["Officers invoked s 20 after observing drug paraphernalia"],
                    "strength": "STRONG",
                    "disposition": "PRIMARY",
                },
                {
                    "rank": 2,
                    "name": "s 30 exclusion of admission",
                    "legal_basis": ["s 30 Evidence Act 2006"],
                    "supporting_facts": ["Admission was unsigned and followed an offer of a formal warning"],
                    "strength": "MODERATE",
                    "disposition": "SECONDARY",
                },
            ],
            "recommended_sections": ["Warrantless Search (s 20)", "s 30 Exclusion"],
        }


@pytest.mark.skipif(_MISSING_FILES, reason=f"Lim disclosure files not found: {_MISSING_FILES}")
def test_lim_pipeline_mentions_central_theory():
    raw = "\n\n".join(f.read_text(encoding="utf-8") for f in TEST_FILES)
    swarm = AgentSwarm(llm_client=TheoryAwareFakeLLM())
    report = swarm.analyse(raw)
    full = "\n".join([
        report.executive_summary,
        report.defence_strategies,
        report.cross_examination_priorities,
        report.evidentiary_issues_to_raise,
        report.conclusion,
    ]).lower()
    assert "s 20" in full or "warrantless" in full or "s 30" in full
