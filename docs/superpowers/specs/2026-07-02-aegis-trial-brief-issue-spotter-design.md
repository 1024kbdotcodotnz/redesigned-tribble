# AEGIS Trial Brief Improvement: Anchored Fact Sheet + Issue Spotter

## Status

Approved design — Option B (Issue-spotter + anchored fact sheet) selected as MVP.

## Problem Statement

The current AEGIS defence-analysis report is generic, unfocused, and misses the strongest legal issues. In the Lim GBL case the human brief identified a single sharp defence — exclusion under s 30 Evidence Act 2006 because the s 20 warrantless search was unlawful and the warrant was overbroad — while the AEGIS report wandered across chain-of-custody, reasonable suspicion, and knowledge without landing on exclusion.

Root causes:
1. Disclosure is flattened into themes; exact quotes, line anchors, and timelines are lost.
2. No component identifies the strongest legal issue / central theory.
3. The six specialist KCs write generic sections rather than ammunition for a single theory.
4. There is no lightweight verification of facts or citations.

## Goal

Produce AEGIS reports that read like the human "Instructions to Counsel":
- A single, defensible central theory.
- Factual claims anchored to exact disclosure sources.
- Per-witness cross-examination derived from officer fact sheets.
- On-point case/statute citations.
- A concise verification/footnote layer.

## Non-Goals

- Rebuild the entire report schema (Option C) — out of scope for this MVP.
- Perfect OCR line-number extraction — use file + approximate line / section name; fall back gracefully.
- Full automated legal research — continue using existing RAG retrieval; issue spotter only *applies* retrieved sources.

## Architecture

```
raw disclosure
    ↓
ParsedDisclosure (existing parser)
    ↓
┌─────────────────────┐
│  Fact Sheet Builder │  ← new
└─────────────────────┘
    ↓
┌─────────────────────┐
│    Issue Spotter    │  ← new
└─────────────────────┘
    ↓
six specialist KCs    ← existing, prompted with fact sheet + theory
    ↓
Orchestrator          ← existing, synthesises around central theory
    ↓
Verification pass     ← new lightweight
    ↓
DOCX/PDF export       ← existing
```

## Component 1: Fact Sheet Builder

### Location

`core/fact_sheet.py` (new module). Called from `AgentSwarm.analyse()` after `DisclosureParser.parse()`.

### Input

- `ParsedDisclosure` dataclass
- Raw disclosure text (per file)
- File names / paths

### Output

A `FactSheet` dataclass serialisable to JSON/dict:

```python
@dataclass
class FactSheet:
    case_meta: CaseMeta
    warrants: List[Warrant]
    timeline: List[TimelineEvent]
    officers: Dict[str, OfficerFacts]
    admissions: List[Admission]
    forensics: List[ForensicItem]
    seized_items: List[SeizedItem]
    not_found_items: List[str]
    gaps: List[str]
```

Sub-schemas:

```python
@dataclass
class CaseMeta:
    defendant: str
    charges: List[Charge]
    court: str
    date: Optional[str]

@dataclass
class Warrant:
    number: str
    offence_authorised: str
    scope: List[str]
    place: str
    items_seized: List[str]
    items_not_found: List[str]

@dataclass
class TimelineEvent:
    datetime: Optional[str]
    event: str
    source: str          # e.g. "Ashby stmt (Scanned_v2.txt:105)"
    actor: Optional[str]

@dataclass
class OfficerFacts:
    name: str
    role: str
    key_quotes: List[Quote]

@dataclass
class Quote:
    text: str
    source: str
    context: str

@dataclass
class Admission:
    date: Optional[str]
    officer: str
    alleged_words: str
    signed: Optional[bool]
    lawyer_present: Optional[bool]
    context: str
    source: str

@dataclass
class SeizedItem:
    description: str
    location: str
    seized_by: str
    time: Optional[str]
    exhibit_number: Optional[str]
    source: str
```

### Extraction strategy

1. **Reuse existing parser output** for charges, dates, court, defendant.
2. **Warrant blocks** — regex for "SEARCH WARRANT", "Section 6", warrant number pattern `SW\d+`, offence text, and bullet lists of evidential material.
3. **Officer statements** — split disclosure by statement headers ("Statement of: <Name>"), extract paragraphs, pull sentences containing keywords relevant to the charge.
4. **Timeline** — regex for time/date patterns near officer names or warrant events; deduplicate and sort.
5. **Admissions** — search for "admitted", "formal warning", "declined to comment", "refused to sign", "lawyer".
6. **Seized items** — regex for "seized", "exhibit", "located" with location context.
7. **Not found items** — detect statements like "no trailer", "not found", "absence of".
8. **Gaps** — list missing expected materials (body-worn camera, custody records, forensic photos) when the text mentions them conditionally.

### Source anchoring

- Use `filename:line` where line numbers are available.
- For OCR without reliable line numbers, use section headers: `"Ashby stmt (Scanned_v2.txt)"`.
- Store the original text snippet with each fact so downstream prompts can quote verbatim.

## Component 2: Issue Spotter

### Location

`core/issue_spotter.py` (new module). Single LLM call.

### Input

- `FactSheet` (JSON)
- Primary charge
- Retrieved legal sources (existing RAG output)

### Output

```python
@dataclass
class IssueSpottingResult:
    central_theory: str
    issues: List[Issue]
    recommended_sections: List[str]

@dataclass
class Issue:
    rank: int
    name: str
    legal_basis: List[str]
    supporting_facts: List[str]
    strength: Literal["STRONG", "MODERATE", "WEAK"]
    disposition: Literal["PRIMARY", "SECONDARY", "BACKUP"]
```

### Prompt strategy

- Low temperature (0.2–0.3).
- Provide a menu of issue categories: search warrant validity, warrantless search, NZBORA s 21, admissions/pressure, forensic reliability, identification, charging abuse.
- Require the model to cite facts from the fact sheet.
- Enforce charge consistency: for a possession charge, do not rank "identification of offender" above "unlawful search" unless the facts clearly support it.

### Caching

- Cache result keyed by fact-sheet hash to avoid repeated calls during testing.

## Component 3: Prompt Injection

### Changes

Add a new preamble to all six KC prompts and the orchestrator prompt:

```markdown
## CASE THEORY
{central_theory}

## RANKED ISSUES
{issues_json}

## FACT SHEET
{fact_sheet_json}

## INSTRUCTIONS
- Write every section as support for the CASE THEORY above.
- Every factual claim must be anchored to a source in the FACT SHEET.
- Do not invent facts, cases, or statutes.
- Cite New Zealand authorities where relevant.
- For cross-examination, use the officer-specific facts and quotes.
```

### Per-KC specialisation

| KC | Added focus |
|---|---|
| Rights | s 20 cumulative requirements, s 21 NZBORA, s 123 plain view, admission voluntariness |
| Strategist | Exclusion narrative: warrant → scope → plain view → s 20 → s 21 → s 30 |
| Evidential | Assess Crown strengths only in light of whether evidence survives exclusion |
| Cross-Exam | Per-witness questions anchored to officer fact sheets |
| Admissions | Unsigned notebook, lawyer presence, formal-warning pressure, charging chronology |
| Disclosure/Forensic | Missing disclosure that would test the theory (bodycam, custody records) |
| Orchestrator | Output a Trial Brief / Instructions to Counsel with the recommended sections |

## Component 4: Lightweight Verification Pass

### Location

`core/verification.py` or inline in `AgentSwarm._sanitize_report_output()`.

### What it checks

1. **Source anchors:** every paragraph should contain a source marker (`[...]`, `(...)`, or a known officer/notebook reference). Flag paragraphs without anchors.
2. **Fact consistency:** for each named officer or exhibit, check that it appears in the fact sheet; flag unknown names.
3. **Citation sanity:** legal citations should match a pattern or appear in retrieved sources; flag invented-looking ones.
4. **Central-theory drift:** check that the executive summary and conclusion explicitly mention the central theory.

### Output

Append a short "Verification Notes" section to the report:
- Unanchored claims flagged for counsel review.
- Any invented-looking citations flagged.
- Do not remove content automatically; flag only.

## Component 5: Export (minimal changes)

- Re-use existing `build_docx` / `build_pdf`.
- Add a new optional title block: "Instructions to Counsel" when the central theory is strong.
- Ensure footnote/source anchors survive DOCX rendering (currently they are plain text, which is acceptable for MVP).

## Data Flow (sequence diagram)

```
AgentSwarm.analyse()
  ├─ parser.parse(disclosure) → ParsedDisclosure
  ├─ fact_sheet_builder.build(ParsedDisclosure, raw_text) → FactSheet
  ├─ rag_engine.retrieve(charge_queries) → legal_sources
  ├─ issue_spotter.spot(FactSheet, charge, legal_sources) → IssueSpottingResult
  ├─ run_kcs(FactSheet, IssueSpottingResult) → KC outputs
  ├─ orchestrator(FactSheet, IssueSpottingResult, KC outputs) → markdown brief
  ├─ verification_pass(markdown, FactSheet) → flagged markdown
  └─ report_export.build_docx(markdown) → DOCX
```

## Error Handling

- If fact sheet extraction fails partially, continue with available fields; do not crash.
- If issue spotter returns an inconsistent top issue (e.g., "identification" for a possession charge with no ID dispute), fall back to the next highest consistent issue.
- If source anchors are missing, the verification pass flags them but does not block report generation.

## Testing Plan

1. **Unit tests for Fact Sheet Builder**
   - Extract warrant number, offence, scope from `adf_scan_ocr_20260323_105350.txt`.
   - Extract Ashby admission chronology (signed/unsigned, lawyer, charge timing).
   - Extract Kirker timeline (10:41 observation → 10:53 s 20).

2. **Unit tests for Issue Spotter**
   - With the Lim fact sheet, the top issue must be "unlawful s 20 warrantless search" or "overbroad warrant".
   - With a different case, the top issue should change appropriately.

3. **Integration test**
   - Run full `AgentSwarm.analyse()` on the Lim disclosure.
   - Verify the output mentions: s 20, s 30, s 21, s 123, Tamiefuna/Roskam/Renson, the 12-minute delay, and per-witness cross-exam.

4. **Regression tests**
   - Run existing `tests/test_report_export.py` and `tests/test_parser.py` to ensure no breakage.

## Open Questions (resolved by this design)

- OCR line numbers are unreliable → use file + section/line fallback.
- Which module owns the fact sheet → new `core/fact_sheet.py`.
- How to prevent hallucinated citations → lightweight verification pass, not a full citation verifier.

## Success Criteria

After implementation, an AEGIS report on the Lim disclosure must:
1. State a clear central theory within the executive summary.
2. Include a warrant-grounds / scope analysis.
3. Include a s 20 lawfulness analysis with the 10:41→10:53 timeline.
4. Include s 21 NZBORA and s 30 exclusion reasoning.
5. Include per-witness cross-examination questions.
6. Anchor factual claims to disclosure sources.

## Out of Scope (future work)

- Full structured trial-brief schema (Option C).
- Automated retrieval and verification of NZ case law.
- Hyperlinked footnotes in DOCX/PDF.
