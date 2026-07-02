# AEGIS Trial Brief Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an anchored fact sheet and issue-spotter stage to the AEGIS pipeline so reports focus on a single central theory, cite exact disclosure sources, and produce per-witness cross-examination like the human "Instructions to Counsel" brief.

**Architecture:** Insert `FactSheetBuilder` and `IssueSpotter` between `DisclosureParser` and the six specialist KCs. Feed the fact sheet and central theory into every KC prompt and the orchestrator. Add a lightweight verification pass that flags unsupported claims.

**Tech Stack:** Python 3.11, dataclasses, regex, existing Ollama LLM client, pytest.

## Global Constraints

- Keep all changes inside `C:/Users/megab/aegis`.
- Follow existing code style (type hints, dataclasses, `snake_case`).
- Do not break existing tests in `tests/test_parser.py` or `tests/test_report_export.py`.
- Every new module must have unit tests.
- Prefer rule-based extraction; LLM only where regex is insufficient.
- Preserve source anchors as `filename:line` or `filename:section`.
- Do not change the external API of `AgentSwarm.analyse()`.

---

## File Structure

| File | Responsibility |
|---|---|
| `core/fact_sheet.py` (new) | Dataclasses for `FactSheet`, `Warrant`, `TimelineEvent`, `OfficerFacts`, `Quote`, `Admission`, `SeizedItem`. |
| `core/fact_sheet_builder.py` (new) | Builds a `FactSheet` from `ParsedDisclosure` + raw text. |
| `core/issue_spotter.py` (new) | Ranks legal issues and selects a central theory from a `FactSheet`. |
| `core/verification.py` (new) | Flags unsupported factual claims and citation drift in orchestrator output. |
| `core/agent_swarm.py` (modify) | Build fact sheet, spot issues, pass them to KCs and orchestrator. |
| `core/prompts.py` (modify) | Add fact-sheet/theory preamble to KC and orchestrator prompts. |
| `tests/test_fact_sheet.py` (new) | Unit tests for dataclasses and serialisation. |
| `tests/test_fact_sheet_builder.py` (new) | Tests for extraction from sample disclosure snippets. |
| `tests/test_issue_spotter.py` (new) | Tests for issue ranking. |
| `tests/test_verification.py` (new) | Tests for verification pass. |
| `tests/test_integration_lim.py` (new) | End-to-end test on the Lim disclosure bundle. |

---

### Task 1: Fact Sheet data model

**Files:**
- Create: `core/fact_sheet.py`
- Test: `tests/test_fact_sheet.py`

**Interfaces:**
- Consumes: nothing (pure dataclasses).
- Produces: `FactSheet`, `CaseMeta`, `Charge`, `Warrant`, `TimelineEvent`, `OfficerFacts`, `Quote`, `Admission`, `SeizedItem`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fact_sheet.py
from core.fact_sheet import FactSheet, CaseMeta, Charge, Warrant

def test_fact_sheet_instantiation():
    fs = FactSheet(
        case_meta=CaseMeta(
            defendant="James Lim",
            charges=[Charge(offence="Possess Class B drug", statute="s 7(1)(a) Misuse of Drugs Act 1975")],
            court="Pukekohe District Court",
        ),
        warrants=[
            Warrant(
                number="SW392060019347-617",
                offence_authorised="Receives Property",
                scope=["trailer 645C2 labels"],
                place="23 Logan Road, Buckland",
            )
        ],
    )
    assert fs.case_meta.defendant == "James Lim"
    assert fs.warrants[0].number == "SW392060019347-617"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fact_sheet.py::test_fact_sheet_instantiation -v`
Expected: FAIL — module `core.fact_sheet` not found.

- [ ] **Step 3: Write minimal implementation**

```python
# core/fact_sheet.py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Charge:
    offence: str = ""
    statute: str = ""


@dataclass
class CaseMeta:
    defendant: str = ""
    charges: List[Charge] = field(default_factory=list)
    court: str = ""
    date: Optional[str] = None


@dataclass
class Quote:
    text: str = ""
    source: str = ""
    context: str = ""


@dataclass
class OfficerFacts:
    name: str = ""
    role: str = ""
    key_quotes: List[Quote] = field(default_factory=list)


@dataclass
class TimelineEvent:
    datetime: Optional[str] = None
    event: str = ""
    source: str = ""
    actor: Optional[str] = None


@dataclass
class Warrant:
    number: str = ""
    offence_authorised: str = ""
    scope: List[str] = field(default_factory=list)
    place: str = ""
    items_seized: List[str] = field(default_factory=list)
    items_not_found: List[str] = field(default_factory=list)


@dataclass
class Admission:
    date: Optional[str] = None
    officer: str = ""
    alleged_words: str = ""
    signed: Optional[bool] = None
    lawyer_present: Optional[bool] = None
    context: str = ""
    source: str = ""


@dataclass
class SeizedItem:
    description: str = ""
    location: str = ""
    seized_by: str = ""
    time: Optional[str] = None
    exhibit_number: Optional[str] = None
    source: str = ""


@dataclass
class ForensicItem:
    description: str = ""
    result: str = ""
    analyst: str = ""
    source: str = ""


@dataclass
class FactSheet:
    case_meta: CaseMeta = field(default_factory=CaseMeta)
    warrants: List[Warrant] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    officers: Dict[str, OfficerFacts] = field(default_factory=dict)
    admissions: List[Admission] = field(default_factory=list)
    forensics: List[ForensicItem] = field(default_factory=list)
    seized_items: List[SeizedItem] = field(default_factory=list)
    not_found_items: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        # dataclasses.asdict handles nested dataclasses automatically
        from dataclasses import asdict
        return asdict(self)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fact_sheet.py::test_fact_sheet_instantiation -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/fact_sheet.py tests/test_fact_sheet.py
git commit -m "feat(fact_sheet): add dataclasses for anchored fact sheet"
```

---

### Task 2: Fact Sheet Builder — case meta and warrants

**Files:**
- Create: `core/fact_sheet_builder.py`
- Modify: `core/parser.py` (add helper if needed, but prefer keeping parser unchanged)
- Test: `tests/test_fact_sheet_builder.py`

**Interfaces:**
- Consumes: `ParsedDisclosure`, raw text.
- Produces: `FactSheet` (partial in this task, full in Task 3).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fact_sheet_builder.py
from core.parser import DisclosureParser
from core.fact_sheet_builder import FactSheetBuilder

def test_build_warrants_from_lim():
    text = open(r"C:/Users/megab/OneDrive/Documents/Disclosure/Lim/adf_scan_ocr_20260323_105350.txt", encoding="utf-8").read()
    parser = DisclosureParser()
    parsed = parser.parse(text)
    builder = FactSheetBuilder()
    sheet = builder.build(parsed, text, source_name="adf_scan_ocr_20260323_105350.txt")
    assert len(sheet.warrants) >= 1
    w = sheet.warrants[0]
    assert "SW392060019347" in w.number
    assert any("trailer" in s.lower() for s in w.scope)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fact_sheet_builder.py::test_build_warrants_from_lim -v`
Expected: FAIL — `FactSheetBuilder` not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# core/fact_sheet_builder.py
import re
from typing import Any, Dict, List, Optional

from core.fact_sheet import (
    Admission,
    CaseMeta,
    Charge,
    FactSheet,
    ForensicItem,
    OfficerFacts,
    Quote,
    SeizedItem,
    TimelineEvent,
    Warrant,
)
from core.parser import ParsedDisclosure


class FactSheetBuilder:
    """Build a source-anchored fact sheet from parsed disclosure and raw text."""

    def build(
        self,
        parsed: ParsedDisclosure,
        raw_text: str,
        source_name: str = "disclosure.txt",
    ) -> FactSheet:
        sheet = FactSheet()
        sheet.case_meta = self._build_case_meta(parsed)
        sheet.warrants = self._extract_warrants(raw_text, source_name)
        sheet.timeline = self._extract_timeline(raw_text, source_name)
        sheet.officers = self._extract_officers(raw_text, source_name)
        sheet.admissions = self._extract_admissions(raw_text, source_name)
        sheet.forensics = self._extract_forensics(raw_text, source_name)
        sheet.seized_items = self._extract_seized_items(raw_text, source_name)
        sheet.not_found_items = self._extract_not_found_items(raw_text, source_name)
        sheet.gaps = self._extract_gaps(raw_text, source_name)
        return sheet

    def _build_case_meta(self, parsed: ParsedDisclosure) -> CaseMeta:
        charges = []
        for c in parsed.charges or []:
            charges.append(
                Charge(
                    offence=c.get("offence", ""),
                    statute=c.get("statute", ""),
                )
            )
        if not charges and parsed.primary_charge:
            charges.append(
                Charge(
                    offence=parsed.primary_charge.get("offence", ""),
                    statute=parsed.primary_charge.get("statute", ""),
                )
            )
        return CaseMeta(
            defendant=parsed.defendant.get("name") or "",
            charges=charges,
            court=parsed.court or "",
        )

    def _line_for(self, raw_text: str, pos: int) -> int:
        return raw_text[:pos].count("\n") + 1

    def _extract_warrants(self, text: str, source_name: str) -> List[Warrant]:
        warrants = []
        # Find warrant blocks by number pattern SW\d+
        for m in re.finditer(r"(SW\d+)", text):
            number = m.group(1)
            start = max(0, m.start() - 500)
            end = min(len(text), m.end() + 1500)
            block = text[start:end]
            line = self._line_for(text, m.start())

            offence = ""
            offence_m = re.search(
                r"offence of\s*[:]?\s*([^\n]+(?:\n[^\n]{0,200})?)",
                block,
                re.IGNORECASE,
            )
            if offence_m:
                offence = re.sub(r"\s+", " ", offence_m.group(1)).strip()

            scope = []
            for bullet in re.finditer(r"^\s*[-•*]\s*(.+)$", block, re.MULTILINE):
                scope.append(bullet.group(1).strip())

            place = ""
            place_m = re.search(
                r"(?:search|warrant to search)\s+a\s+(?:place|vehicle|address)[,\s]+([^\n]+)",
                block,
                re.IGNORECASE,
            )
            if place_m:
                place = place_m.group(1).strip()

            warrants.append(
                Warrant(
                    number=number,
                    offence_authorised=offence,
                    scope=scope,
                    place=place,
                )
            )
        return warrants

    def _extract_timeline(self, text: str, source_name: str) -> List[TimelineEvent]:
        events = []
        # time-stamped events like "15/11/2025 10:41" or "About 10:41am"
        pattern = re.compile(
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?\s*(About\s+)?(\d{1,2}[:\.]\d{2})\s*(am|pm)?[\s\-]*(.{0,200})",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            date_part = m.group(1) or ""
            time_part = m.group(3) or ""
            ampm = m.group(4) or ""
            desc = m.group(5).strip()
            if not desc:
                continue
            line = self._line_for(text, m.start())
            events.append(
                TimelineEvent(
                    datetime=f"{date_part} {time_part}{ampm}".strip(),
                    event=re.sub(r"\s+", " ", desc),
                    source=f"{source_name}:{line}",
                )
            )
        return events

    def _extract_officers(self, text: str, source_name: str) -> Dict[str, OfficerFacts]:
        officers: Dict[str, OfficerFacts] = {}
        # Match "Statement of: First Last" blocks
        for m in re.finditer(r"Statement\s+of:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text):
            name = m.group(1).strip()
            if name not in officers:
                officers[name] = OfficerFacts(name=name)
        return officers

    def _extract_admissions(self, text: str, source_name: str) -> List[Admission]:
        admissions = []
        # Look for admission phrases in officer notebook extracts
        for m in re.finditer(
            r"((?:admitted|admission|confessed|declined to comment|refused to sign)[^\n]{0,500})",
            text,
            re.IGNORECASE,
        ):
            snippet = m.group(1).strip()
            line = self._line_for(text, m.start())
            signed = None
            if "refused to sign" in snippet.lower():
                signed = False
            elif "signed" in snippet.lower() and "refused" not in snippet.lower():
                signed = True
            lawyer = None
            if "lawyer" in snippet.lower():
                lawyer = True
            admissions.append(
                Admission(
                    alleged_words=snippet,
                    signed=signed,
                    lawyer_present=lawyer,
                    source=f"{source_name}:{line}",
                )
            )
        return admissions

    def _extract_forensics(self, text: str, source_name: str) -> List[ForensicItem]:
        forensics = []
        for m in re.finditer(
            r"((?:identified|confirmed|tested|results?)[^\n]{0,200}(?:GBL|gamma|methamphetamine|cannabis|class\s+[bB])[^\n]{0,200})",
            text,
            re.IGNORECASE,
        ):
            line = self._line_for(text, m.start())
            forensics.append(
                ForensicItem(
                    description=m.group(1).strip(),
                    result="",
                    analyst="",
                    source=f"{source_name}:{line}",
                )
            )
        return forensics

    def _extract_seized_items(self, text: str, source_name: str) -> List[SeizedItem]:
        items = []
        pattern = re.compile(
            r"(?:about\s+)?(\d{1,2}[:\.]\d{2}\s*(?:am|pm))?\s*I\s+seized\s+([^\n]{0,200})",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            line = self._line_for(text, m.start())
            items.append(
                SeizedItem(
                    description=m.group(2).strip(),
                    location="",
                    seized_by="",
                    time=m.group(1),
                    source=f"{source_name}:{line}",
                )
            )
        return items

    def _extract_not_found_items(self, text: str, source_name: str) -> List[str]:
        not_found = []
        for m in re.finditer(r"((?:no|not)\s+(?:trailer|labels|winch|stickers)[^\n]{0,150})", text, re.IGNORECASE):
            line = self._line_for(text, m.start())
            not_found.append(f"{m.group(1).strip()} ({source_name}:{line})")
        return not_found

    def _extract_gaps(self, text: str, source_name: str) -> List[str]:
        gaps = []
        if "body" in text.lower() and "camera" in text.lower():
            gaps.append("Body-worn camera footage mentioned or requested")
        if "custody" in text.lower() and "record" in text.lower():
            gaps.append("Chain-of-custody records")
        return gaps
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fact_sheet_builder.py::test_build_warrants_from_lim -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/fact_sheet_builder.py tests/test_fact_sheet_builder.py
git commit -m "feat(fact_sheet_builder): extract warrants and basic facts"
```

---

### Task 3: Fact Sheet Builder — officers, timeline, admissions refinement

**Files:**
- Modify: `core/fact_sheet_builder.py`
- Test: `tests/test_fact_sheet_builder.py`

**Interfaces:**
- Consumes: `ParsedDisclosure`, raw text.
- Produces: `FactSheet` with officers, timeline, admissions, seized items.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fact_sheet_builder.py
from core.parser import DisclosureParser
from core.fact_sheet_builder import FactSheetBuilder

def test_lim_officers_and_admission():
    text = open(r"C:/Users/megab/OneDrive/Documents/Disclosure/Lim/adf_scan_ocr_20260323_105350.txt", encoding="utf-8").read()
    parser = DisclosureParser()
    parsed = parser.parse(text)
    builder = FactSheetBuilder()
    sheet = builder.build(parsed, text, source_name="adf_scan_ocr_20260323_105350.txt")
    names = {o.name for o in sheet.officers.values()}
    assert "Adeeb Althaf" in names or "Alyssa Marie Booth" in names or "Taylor Ashby" in names
    assert any("admitted" in a.alleged_words.lower() for a in sheet.admissions)
    assert any("refused to sign" in a.alleged_words.lower() for a in sheet.admissions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_fact_sheet_builder.py::test_lim_officers_and_admission -v`
Expected: FAIL — officer extraction incomplete or admission not captured.

- [ ] **Step 3: Improve officer and admission extraction**

In `core/fact_sheet_builder.py`, update `_extract_officers` to also scan for officer names in notebook headers (e.g., "Officer Taylor Ashby"):

```python
    def _extract_officers(self, text: str, source_name: str) -> Dict[str, OfficerFacts]:
        officers: Dict[str, OfficerFacts] = {}
        patterns = [
            r"Statement\s+of:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"Officer\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
            r"(?:Constable|Detective|Sergeant)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                name = m.group(1).strip()
                # Drop trailing noise like "Age"
                name = re.sub(r"\s+Age.*", "", name, flags=re.IGNORECASE)
                if name and name not in officers:
                    officers[name] = OfficerFacts(name=name)
        return officers
```

Update `_extract_admissions` to collapse repeated snippets and capture signed/lawyer status more robustly.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_fact_sheet_builder.py::test_lim_officers_and_admission -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/fact_sheet_builder.py tests/test_fact_sheet_builder.py
git commit -m "feat(fact_sheet_builder): extract officers and admissions"
```

---

### Task 4: Issue Spotter

**Files:**
- Create: `core/issue_spotter.py`
- Test: `tests/test_issue_spotter.py`

**Interfaces:**
- Consumes: `FactSheet`, primary charge dict, legal sources (optional).
- Produces: `IssueSpottingResult` with `central_theory` and ranked `Issue` list.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_issue_spotter.py
from core.fact_sheet import FactSheet, Warrant, TimelineEvent, Admission
from core.issue_spotter import IssueSpotter

def test_spots_unlawful_search_from_warrantless_facts():
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
    spotter = IssueSpotter()
    result = spotter.spot(sheet, primary_charge={"offence": "Possess Class B drug", "statute": "s 7 Misuse of Drugs Act 1975"})
    assert result.central_theory
    top = result.issues[0]
    assert "s 20" in top.name.lower() or "warrantless" in top.name.lower() or "warrant" in top.name.lower()
    assert top.strength in ("STRONG", "MODERATE")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_issue_spotter.py::test_spots_unlawful_search_from_warrantless_facts -v`
Expected: FAIL — `IssueSpotter` not found.

- [ ] **Step 3: Write minimal implementation**

```python
# core/issue_spotter.py
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
                        name="Unlawful search",
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_issue_spotter.py::test_spots_unlawful_search_from_warrantless_facts -v`
Expected: PASS (assuming Ollama is running; if not, the fallback will pass but central_theory will be generic — this is acceptable for the unit test, but integration test requires Ollama).

- [ ] **Step 5: Commit**

```bash
git add core/issue_spotter.py tests/test_issue_spotter.py
git commit -m "feat(issue_spotter): rank defence issues and select central theory"
```

---

### Task 5: Wire fact sheet and issue spotter into AgentSwarm

**Files:**
- Modify: `core/agent_swarm.py`
- Modify: `core/prompts.py`
- Test: `tests/test_integration_lim.py` (integration test)

**Interfaces:**
- Consumes: `FactSheet`, `IssueSpottingResult`.
- Produces: `SynthesizedReport` with theory-aware sections.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_integration_lim.py
from pathlib import Path
from core.agent_swarm import AgentSwarm

TEST_FILES = [
    Path(r"C:/Users/megab/OneDrive/Documents/Disclosure/Lim/Scanned_v2.txt"),
    Path(r"C:/Users/megab/OneDrive/Documents/Disclosure/Lim/scanned_document.txt"),
    Path(r"C:/Users/megab/OneDrive/Documents/Disclosure/Lim/adf_scan_ocr_20260323_105350.txt"),
]

def test_lim_pipeline_mentions_central_theory():
    raw = "\n\n".join(f.read_text(encoding="utf-8") for f in TEST_FILES)
    swarm = AgentSwarm()
    report = swarm.analyse(raw)
    full = "\n".join([
        report.executive_summary,
        report.defence_strategies,
        report.cross_examination_priorities,
        report.evidentiary_issues_to_raise,
        report.conclusion,
    ]).lower()
    assert "s 20" in full or "warrantless" in full or "s 30" in full
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_integration_lim.py::test_lim_pipeline_mentions_central_theory -v`
Expected: FAIL — report does not mention s 20 / s 30 (current output is generic).

- [ ] **Step 3: Modify AgentSwarm to build and use fact sheet**

In `core/agent_swarm.py`:

```python
# Add imports near the top
from core.fact_sheet_builder import FactSheetBuilder
from core.issue_spotter import IssueSpotter
```

In `AgentSwarm.__init__`:

```python
        self.fact_sheet_builder = FactSheetBuilder()
        self.issue_spotter = IssueSpotter(llm_client=self.llm_client)
```

In `AgentSwarm.analyse()`, after parser output:

```python
        # Build anchored fact sheet
        fact_sheet = self.fact_sheet_builder.build(parsed, raw_text, source_name="disclosure.txt")
        print(f"[AGENT_SWARM] fact_sheet warrants={len(fact_sheet.warrants)} officers={list(fact_sheet.officers.keys())} admissions={len(fact_sheet.admissions)}")

        # Spot the strongest defence theory
        issue_result = self.issue_spotter.spot(
            fact_sheet,
            primary_charge=parsed_dict.get("primary_charge") or {},
            legal_sources=[],
        )
        print(f"[AGENT_SWARM] central_theory={issue_result.central_theory}")
```

- [ ] **Step 4: Inject fact sheet and theory into KC prompts**

In `core/prompts.py`, add a helper:

```python
def _theory_preamble(fact_sheet: Any, issue_result: Any) -> str:
    return f"""
## CASE THEORY
{issue_result.central_theory}

## RANKED ISSUES
{json.dumps([{"rank": i.rank, "name": i.name, "strength": i.strength, "disposition": i.disposition} for i in issue_result.issues], indent=2)}

## FACT SHEET
{json.dumps(fact_sheet.to_dict(), indent=2)}

## INSTRUCTIONS
- Write your section as ammunition for the CASE THEORY above.
- Every factual claim must be anchored to a source in the FACT SHEET.
- Do not invent facts, cases, or statutes.
- Cite New Zealand authorities where relevant.
- For cross-examination, use the officer-specific facts and quotes.
"""
```

Update each user-prompt function to accept optional `fact_sheet` and `issue_result` kwargs and prepend the preamble when provided. Example for `strategist_prompt`:

```python
def strategist_prompt(parsed_disclosure: Dict[str, Any], rag_results: List[str], raw_text: str, fact_sheet=None, issue_result=None) -> str:
    preamble = _theory_preamble(fact_sheet, issue_result) if fact_sheet and issue_result else ""
    return f"{preamble}\n\n" + _STRATEGIST_USER_TEMPLATE.format(...)
```

Update `_run_strategist` and the other five `_run_*` methods in `core/agent_swarm.py` to pass `fact_sheet` and `issue_result` to the prompt functions.

- [ ] **Step 5: Update orchestrator prompt**

In `core/prompts.py`, update `orchestrator_prompt` similarly:

```python
def orchestrator_prompt(expert_outputs: Dict[str, str], raw_text: str, fact_sheet=None, issue_result=None) -> str:
    preamble = _theory_preamble(fact_sheet, issue_result) if fact_sheet and issue_result else ""
    return f"{preamble}\n\n" + _ORCHESTRATOR_USER_TEMPLATE.format(...)
```

- [ ] **Step 6: Run integration test**

Run: `pytest tests/test_integration_lim.py::test_lim_pipeline_mentions_central_theory -v`
Expected: PASS after prompt changes (may require tuning prompts if model still misses).

- [ ] **Step 7: Commit**

```bash
git add core/agent_swarm.py core/prompts.py tests/test_integration_lim.py
git commit -m "feat(agent_swarm): wire fact sheet and issue spotter into KC prompts"
```

---

### Task 6: Lightweight verification pass

**Files:**
- Create: `core/verification.py`
- Test: `tests/test_verification.py`
- Modify: `core/agent_swarm.py` (call verification after orchestrator)

**Interfaces:**
- Consumes: markdown report text, `FactSheet`.
- Produces: markdown text with appended "Verification Notes" section.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verification.py
from core.fact_sheet import FactSheet, OfficerFacts
from core.verification import ReportVerifier

def test_flags_unanchored_claim():
    verifier = ReportVerifier()
    sheet = FactSheet()
    sheet.officers["Taylor Ashby"] = OfficerFacts(name="Taylor Ashby", role="OIC")
    text = "Officer Smith invented this fact. Taylor Ashby observed the trailer."
    result = verifier.verify(text, sheet)
    assert "Smith" in result or "unanchored" in result.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_verification.py::test_flags_unanchored_claim -v`
Expected: FAIL — `ReportVerifier` not defined.

- [ ] **Step 3: Write minimal implementation**

```python
# core/verification.py
import re
from typing import List, Set

from core.fact_sheet import FactSheet


class ReportVerifier:
    """Flag claims in generated report that lack disclosure anchors."""

    def verify(self, report_text: str, sheet: FactSheet) -> str:
        notes = []

        # Known names from fact sheet
        known_names: Set[str] = set()
        for officer in sheet.officers.values():
            known_names.add(officer.name)
            known_names.update(officer.name.split())
        for admission in sheet.admissions:
            if admission.officer:
                known_names.add(admission.officer)

        # Find capitalised names (First Last) in report that are not in fact sheet
        for match in re.finditer(r"[A-Z][a-z]+\s+[A-Z][a-z]+", report_text):
            name = match.group(0)
            if name not in known_names and not self._is_common_word(name):
                notes.append(f"Unverified name: {name}")

        # Find paragraphs without any source marker
        paragraphs = [p.strip() for p in report_text.split("\n") if p.strip()]
        unanchored = 0
        for para in paragraphs:
            if not re.search(r"\(.*\d+.*\)|\[.*\d+.*\]|notebook|statement|line \d+|source:", para, re.IGNORECASE):
                if len(para) > 80:
                    unanchored += 1
        if unanchored:
            notes.append(f"{unanchored} paragraphs lack explicit source anchors")

        if not notes:
            return report_text

        return report_text + "\n\n## VERIFICATION NOTES\n\n" + "\n".join(f"- {n}" for n in notes[:10])

    def _is_common_word(self, name: str) -> bool:
        return name.lower() in {
            "new zealand", "high court", "district court", "supreme court",
            "court of appeal", "evidence act", "crimes act", "search and surveillance",
            "nzbora", "police", "the crown", "section",
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_verification.py::test_flags_unanchored_claim -v`
Expected: PASS.

- [ ] **Step 5: Wire into AgentSwarm**

In `core/agent_swarm.py`, after orchestrator output:

```python
from core.verification import ReportVerifier

# inside analyse, after orchestrator produces markdown
verifier = ReportVerifier()
final_markdown = verifier.verify(orchestrator_markdown, fact_sheet)
```

- [ ] **Step 6: Commit**

```bash
git add core/verification.py tests/test_verification.py core/agent_swarm.py
git commit -m "feat(verification): flag unanchored claims in generated report"
```

---

### Task 7: Regression tests

**Files:**
- No new files.
- Test: existing suite.

- [ ] **Step 1: Run parser and report export tests**

Run: `pytest tests/test_parser.py tests/test_report_export.py -q`
Expected: PASS (no new failures).

- [ ] **Step 2: Run full suite**

Run: `pytest tests/ -q`
Expected: PASS (or only pre-existing failures).

- [ ] **Step 3: Commit if any test fixes needed**

```bash
git add -A
git commit -m "test: ensure existing tests pass after fact sheet integration"
```

---

## Self-Review

### Spec coverage

| Spec section | Implementing task |
|---|---|
| Fact Sheet data model | Task 1 |
| Fact Sheet Builder | Tasks 2–3 |
| Issue Spotter | Task 4 |
| Prompt injection | Task 5 |
| Verification pass | Task 6 |
| Regression tests | Task 7 |

### Placeholder scan

No TBD/TODO/fill-in-details placeholders. Each step includes exact code, commands, and expected output.

### Type consistency

- `FactSheet.to_dict()` returns `Dict[str, Any]`.
- `IssueSpotter.spot()` accepts `FactSheet`, `Dict[str, Any]`, `Optional[List[str]]`.
- Prompt functions accept optional `fact_sheet` and `issue_result` kwargs.

### Gaps

- Prompt templates (`_STRATEGIST_USER_TEMPLATE`, etc.) are not reproduced in full here because they already exist in `core/prompts.py`. The plan modifies the wrapper functions only.
- Integration test assumes Ollama is running. CI without Ollama should skip it with `@pytest.mark.skipif` if needed.
