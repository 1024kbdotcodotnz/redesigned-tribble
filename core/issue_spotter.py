import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.fact_sheet import FactSheet
from core.agent_swarm import OllamaLLMClient


@dataclass
class Issue:
    rank: int
    name: str
    legal_basis: List[str] = field(default_factory=list)
    supporting_facts: List[str] = field(default_factory=list)
    strength: str = "MODERATE"
    disposition: str = "SECONDARY"


@dataclass
class IssueSpottingResult:
    central_theory: str = ""
    issues: List[Issue] = field(default_factory=list)
    recommended_sections: List[str] = field(default_factory=list)


class IssueSpotter:
    """Select the strongest defence theory from an anchored fact sheet."""

    DEFAULT_SECTIONS = [
        "Warrant Grounds",
        "Scope Overreach",
        "Plain View (s 123)",
        "Warrantless Search (s 20)",
        "NZBORA s 21",
        "Admissions and Charging",
        "s 30 Exclusion",
        "Cross-Examination",
    ]

    def __init__(self, llm_client: Optional[OllamaLLMClient] = None):
        self.llm_client = llm_client or OllamaLLMClient(
            model=os.getenv("ISSUE_SPOTTER_MODEL", "qwen2.5:14b"),
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        )

    def spot(
        self,
        sheet: FactSheet,
        primary_charge: Dict[str, Any],
        legal_sources: Optional[List[str]] = None,
    ) -> IssueSpottingResult:
        prompt = self._build_prompt(sheet, primary_charge, legal_sources or [])
        response = self.llm_client.generate_json(
            prompt,
            system=self._system_prompt(),
            temperature=0.2,
            max_tokens=3000,
        )
        return self._parse_response(response)

    def _system_prompt(self) -> str:
        return (
            "You are a senior New Zealand criminal defence counsel. "
            "Read the provided fact sheet and identify the 3-5 strongest legal issues. "
            "Rank them. Choose one central theory of the case. "
            "Return valid JSON only."
        )

    def _build_prompt(
        self,
        sheet: FactSheet,
        primary_charge: Dict[str, Any],
        legal_sources: List[str],
    ) -> str:
        return f"""
Fact Sheet:
{sheet.to_dict()}

Primary Charge:
{primary_charge}

Optional legal sources already retrieved:
{chr(10).join(legal_sources[:5])}

Instructions:
1. Identify the 3-5 strongest legal issues for the defence.
2. For each issue, give: rank (1 highest), name, legal_basis (statutes/cases), supporting_facts (from the fact sheet), strength (STRONG/MODERATE/WEAK), disposition (PRIMARY/SECONDARY/BACKUP).
3. Provide a single concise "central_theory" sentence that counsel would use as the case theory.
4. Provide "recommended_sections" for a trial brief.

Return JSON in this exact schema:
{{
  "central_theory": "...",
  "issues": [
    {{
      "rank": 1,
      "name": "...",
      "legal_basis": ["..."],
      "supporting_facts": ["..."],
      "strength": "STRONG",
      "disposition": "PRIMARY"
    }}
  ],
  "recommended_sections": ["..."]
}}
"""

    def _parse_response(self, response: Dict[str, Any]) -> IssueSpottingResult:
        if "error" in response:
            # Fallback to a generic theory if JSON parsing failed
            return IssueSpottingResult(
                central_theory="Challenge the lawfulness of the search and the reliability of the Crown evidence.",
                issues=[
                    Issue(
                        rank=1,
                        name="Warrantless search",
                        legal_basis=["s 21 NZBORA", "s 30 Evidence Act 2006"],
                        supporting_facts=["Search and seizure circumstances require scrutiny"],
                        strength="MODERATE",
                        disposition="PRIMARY",
                    )
                ],
                recommended_sections=self.DEFAULT_SECTIONS,
            )

        issues = []
        for item in response.get("issues", []):
            issues.append(
                Issue(
                    rank=int(item.get("rank", 99)),
                    name=item.get("name", ""),
                    legal_basis=item.get("legal_basis", []),
                    supporting_facts=item.get("supporting_facts", []),
                    strength=item.get("strength", "MODERATE"),
                    disposition=item.get("disposition", "SECONDARY"),
                )
            )

        return IssueSpottingResult(
            central_theory=response.get("central_theory", ""),
            issues=sorted(issues, key=lambda i: i.rank),
            recommended_sections=response.get("recommended_sections", self.DEFAULT_SECTIONS),
        )
