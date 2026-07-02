from typing import Any, Dict

from core.fact_sheet import FactSheet, Warrant, TimelineEvent, Admission
from core.issue_spotter import IssueSpotter


class FakeLLMClient:
    """Deterministic LLM client for testing issue-spotter parsing."""

    def __init__(self, response: Dict[str, Any]):
        self.response = response
        self.last_prompt: str = ""
        self.last_system: str = ""

    def generate_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        self.last_prompt = prompt
        self.last_system = system
        return self.response


def _sample_sheet() -> FactSheet:
    sheet = FactSheet()
    sheet.warrants = [
        Warrant(
            number="SW392060019347-617",
            offence_authorised="Receives Property",
            scope=["trailer 645C2 labels"],
            place="23 Logan Road",
            items_not_found=["trailer not found at property"],
        )
    ]
    sheet.timeline = [
        TimelineEvent(datetime="15/11/2025 10:41", event="observed pipe and droppers", source="Kirker notebook"),
        TimelineEvent(datetime="15/11/2025 10:53", event="invoked s 20 search for drugs", source="Kirker notebook"),
    ]
    sheet.admissions = [
        Admission(
            alleged_words="admitted GBL was correct, later refused to sign",
            signed=False,
            lawyer_present=True,
            source="Ashby notebook",
        )
    ]
    return sheet


def test_spots_unlawful_search_from_warrantless_facts():
    sheet = _sample_sheet()
    fake_response = {
        "central_theory": "The warrantless search and unsigned admission undermine the Crown case.",
        "issues": [
            {
                "rank": 1,
                "name": "Warrantless search under s 20",
                "legal_basis": ["s 20 Misuse of Drugs Act 1975", "s 21 NZBORA"],
                "supporting_facts": ["Officers invoked s 20 after observing pipe"],
                "strength": "STRONG",
                "disposition": "PRIMARY",
            },
            {
                "rank": 2,
                "name": "Unreliable admission",
                "legal_basis": ["s 28 Evidence Act 2006"],
                "supporting_facts": ["Admitted GBL but refused to sign"],
                "strength": "MODERATE",
                "disposition": "SECONDARY",
            },
        ],
        "recommended_sections": ["Warrantless Search (s 20)", "Admissions and Charging"],
    }
    spotter = IssueSpotter(llm_client=FakeLLMClient(fake_response))
    result = spotter.spot(sheet, primary_charge={"offence": "Possess Class B drug", "statute": "s 7 Misuse of Drugs Act 1975"})

    assert result.central_theory == fake_response["central_theory"]
    assert len(result.issues) == 2
    top = result.issues[0]
    assert "s 20" in top.name.lower() or "warrantless" in top.name.lower() or "warrant" in top.name.lower()
    assert top.strength == "STRONG"
    assert top.disposition == "PRIMARY"
    assert result.issues[1].strength == "MODERATE"
    assert result.recommended_sections == fake_response["recommended_sections"]


def test_fallback_populates_concrete_supporting_facts():
    sheet = _sample_sheet()
    fake_response = {"error": "model unavailable"}
    spotter = IssueSpotter(llm_client=FakeLLMClient(fake_response))
    result = spotter.spot(sheet, primary_charge={"offence": "Possess Class B drug", "statute": "s 7 Misuse of Drugs Act 1975"})

    assert result.central_theory
    issue = result.issues[0]
    assert any("s 20" in fact for fact in issue.supporting_facts)
    assert any("admitted GBL" in fact for fact in issue.supporting_facts)
    assert any("trailer not found" in fact for fact in issue.supporting_facts)


def test_invalid_strength_and_disposition_default_to_safe_values():
    sheet = _sample_sheet()
    fake_response = {
        "central_theory": "Theory",
        "issues": [
            {
                "rank": 1,
                "name": "Bad values",
                "legal_basis": [],
                "supporting_facts": [],
                "strength": "HUGE",
                "disposition": "MAYBE",
            },
            {
                "rank": 2,
                "name": "Lowercase values",
                "legal_basis": [],
                "supporting_facts": [],
                "strength": "strong",
                "disposition": "backup",
            },
        ],
        "recommended_sections": [],
    }
    spotter = IssueSpotter(llm_client=FakeLLMClient(fake_response))
    result = spotter.spot(sheet, primary_charge={"offence": "Possess Class B drug", "statute": "s 7 Misuse of Drugs Act 1975"})

    assert result.issues[0].strength == "MODERATE"
    assert result.issues[0].disposition == "SECONDARY"
    assert result.issues[1].strength == "STRONG"
    assert result.issues[1].disposition == "BACKUP"
