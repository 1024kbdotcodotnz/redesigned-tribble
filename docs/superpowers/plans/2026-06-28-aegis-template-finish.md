# AEGIS DOCX/PDF Analysis Output Template — Finish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the AEGIS defence-analysis export template by adding the three pipeline sections that currently appear in the UI but are missing from DOCX/PDF output, and add regression tests for the export builders.

**Architecture:** `aegis/core/report_export.py` already builds DOCX (via `python-docx`) and PDF (via `docx2pdf`/Word, with an `fpdf2` fallback). The only change needed is to expand the shared `_MAIN_SECTIONS` list so it matches the sections rendered by the Streamlit UI. A new `aegis/tests/test_report_export.py` file will exercise `build_docx`, `build_html`, and the fallback `build_pdf` path.

**Tech Stack:** Python, python-docx, fpdf2, docx2pdf, pytest.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `aegis/core/report_export.py` | Shared `_MAIN_SECTIONS` list; DOCX/PDF builders consume it. |
| `aegis/tests/test_report_export.py` (new) | Regression tests for DOCX, HTML, and PDF fallback exports. |

---

## Task 1: Add Missing Pipeline Sections to `_MAIN_SECTIONS`

**Files:**
- Modify: `aegis/core/report_export.py:69-79`

The Streamlit UI renders these sections in order:

1. Executive Summary
2. Charge and Legislative Framework
3. Summary of Evidence
4. Assessment of Prosecution Case
5. Evidence Analysis
6. Elements the Prosecution Must Prove
7. Defence Strategies and Options
8. Cross-Examination Priorities
9. Disclosure and Forensic Gaps
10. Instructions to Counsel Pre-Trial
11. Evidentiary Issues to Raise
12. Conclusion

`core/report_export.py` currently omits `evidence_analysis`, `cross_examination_priorities`, and `disclosure_and_forensic_gaps`.

- [ ] **Step 1: Replace the `_MAIN_SECTIONS` definition**

```python
# Main sections shared between DOCX and PDF builders.
_MAIN_SECTIONS = [
    ("executive_summary", "EXECUTIVE SUMMARY"),
    ("charge_and_legislative_framework", "CHARGE AND LEGISLATIVE FRAMEWORK"),
    ("summary_of_evidence", "SUMMARY OF EVIDENCE"),
    ("assessment_of_prosecution_case", "ASSESSMENT OF PROSECUTION CASE"),
    ("evidence_analysis", "EVIDENCE ANALYSIS"),
    ("elements_of_the_offence", "ELEMENTS THE PROSECUTION MUST PROVE"),
    ("defence_strategies", "DEFENCE STRATEGIES AND OPTIONS"),
    ("cross_examination_priorities", "CROSS-EXAMINATION PRIORITIES"),
    ("disclosure_and_forensic_gaps", "DISCLOSURE AND FORENSIC GAPS"),
    ("instructions_to_counsel_pre_trial", "INSTRUCTIONS TO COUNSEL PRE-TRIAL"),
    ("evidentiary_issues_to_raise", "EVIDENTIARY ISSUES TO RAISE"),
    ("conclusion", "CONCLUSION"),
]
```

- [ ] **Step 2: Run syntax check**

```bash
cd aegis && .venv/Scripts/python -m py_compile core/report_export.py
```

Expected: exit 0, no output.

- [ ] **Step 3: Commit**

```bash
cd aegis && git add core/report_export.py && git commit -m "feat(report): include evidence_analysis, cross-examination and disclosure sections in exports"
```

---

## Task 2: Create Regression Tests

**Files:**
- Create: `aegis/tests/test_report_export.py`

- [ ] **Step 1: Create the test directory and file**

```bash
mkdir -p aegis/tests
```

```python
# aegis/tests/test_report_export.py
import datetime
from io import BytesIO

import pytest

from core.report_export import build_docx, build_html, build_pdf


def _sample_result():
    return {
        "title_block": "Court: Auckland District Court\nCharge: Burglary\nStatute: Crimes Act 1961, s 231",
        "executive_summary": "The prosecution case depends on identification evidence.",
        "charge_and_legislative_framework": "Charge: Burglary\nStatute: Crimes Act 1961, s 231",
        "summary_of_evidence": "1. CCTV footage shows an individual entering the store.\n2. A witness statement describes the suspect.",
        "assessment_of_prosecution_case": "The identification evidence is weak.",
        "evidence_analysis": "CCTV quality is poor and the witness view was brief.",
        "elements_of_the_offence": "1. The defendant entered a building as a trespasser.\n2. The defendant intended to commit a crime inside.",
        "defence_strategies": "Strategy Name: Challenge identification\n**Objective:** Undermine the reliability of the CCTV evidence.",
        "cross_examination_priorities": "1. Confirm the camera angle and lighting conditions.\n2. Establish how long the witness observed the suspect.",
        "disclosure_and_forensic_gaps": "- Chain-of-custody records for seized exhibits\n- Original unedited CCTV footage",
        "instructions_to_counsel_pre_trial": "Obtain the original CCTV footage.",
        "evidentiary_issues_to_raise": "Legal Basis: Evidence Act 2006, s 23\nReliability of the alleged identification.",
        "conclusion": "The defence has a realistic prospect of acquittal.",
        "disclaimer": "This analysis is generated by AI and does not constitute legal advice.",
        "success": True,
    }


def test_build_docx_creates_valid_buffer():
    buf = build_docx(_sample_result())
    assert isinstance(buf, BytesIO)
    data = buf.getvalue()
    assert data.startswith(b"PK")
    assert len(data) > 1000


def test_build_docx_contains_all_main_sections():
    from docx import Document

    buf = build_docx(_sample_result())
    doc = Document(buf)
    full_text = "\n".join(p.text for p in doc.paragraphs)
    expected_headings = [
        "1. EXECUTIVE SUMMARY",
        "2. CHARGE AND LEGISLATIVE FRAMEWORK",
        "3. SUMMARY OF EVIDENCE",
        "4. ASSESSMENT OF PROSECUTION CASE",
        "5. EVIDENCE ANALYSIS",
        "6. ELEMENTS THE PROSECUTION MUST PROVE",
        "7. DEFENCE STRATEGIES AND OPTIONS",
        "8. CROSS-EXAMINATION PRIORITIES",
        "9. DISCLOSURE AND FORENSIC GAPS",
        "10. INSTRUCTIONS TO COUNSEL PRE-TRIAL",
        "11. EVIDENTIARY ISSUES TO RAISE",
        "12. CONCLUSION",
    ]
    for heading in expected_headings:
        assert heading in full_text, f"Missing heading: {heading}"


def test_build_html_contains_brand_and_sections():
    html = build_html(_sample_result())
    assert "AEGIS" in html
    assert "Auckland District Court" in html
    assert "CROSS-EXAMINATION PRIORITIES" in html
    assert "DISCLOSURE AND FORENSIC GAPS" in html
    assert "EVIDENCE ANALYSIS" in html


def test_build_pdf_falls_back_to_fpdf(monkeypatch):
    """When docx2pdf is unavailable, build_pdf must return a valid PDF buffer."""
    import sys
    import core.report_export as re_mod

    # Make docx2pdf unimportable for the duration of the call.
    monkeypatch.setitem(sys.modules, "docx2pdf", None)
    # In case the module was previously imported, remove the cached reference.
    monkeypatch.setattr(re_mod, "convert", None, raising=False)

    buf = build_pdf(_sample_result())
    assert isinstance(buf, BytesIO)
    data = buf.getvalue()
    assert data.startswith(b"%PDF")
    assert len(data) > 1000
```

- [ ] **Step 2: Install pytest in the project virtual environment**

```bash
cd aegis && .venv/Scripts/python -m pip install pytest
```

Expected: pytest installs successfully.

- [ ] **Step 3: Run the tests**

```bash
cd aegis && .venv/Scripts/python -m pytest tests/test_report_export.py -v
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
cd aegis && git add tests/test_report_export.py && git commit -m "test(report): add regression tests for DOCX, HTML and PDF fallback exports"
```

---

## Task 3: Manual Verification

**Files:**
- None (manual)

- [ ] **Step 1: Generate sample DOCX and PDF outputs**

```bash
cd aegis && .venv/Scripts/python - <<'PY'
from pathlib import Path
from core.report_export import build_docx, build_pdf

# Import the sample fixture by executing the test module.
import runpy
mod = runpy.run_path("tests/test_report_export.py")
result = mod["_sample_result"]()

out_dir = Path("/tmp/aegis_export_samples")
out_dir.mkdir(parents=True, exist_ok=True)

with open(out_dir / "aegis_test.docx", "wb") as f:
    f.write(build_docx(result).getvalue())

with open(out_dir / "aegis_test.pdf", "wb") as f:
    f.write(build_pdf(result).getvalue())

print(f"Written {out_dir / 'aegis_test.docx'}")
print(f"Written {out_dir / 'aegis_test.pdf'}")
PY
```

Expected: two files created; printout shows paths.

- [ ] **Step 2: Inspect DOCX in Microsoft Word**

Open `/tmp/aegis_export_samples/aegis_test.docx` and verify:
- Brand header appears on every page.
- Footer shows brand, prepared date, and page number.
- All 12 main section headings are present and numbered sequentially.
- No section heading sits alone at the bottom of a page.

- [ ] **Step 3: Inspect PDF**

Open `/tmp/aegis_export_samples/aegis_test.pdf` and confirm it contains the same 12 numbered sections and AEGIS header/footer.

---

## Self-Review Checklist

- [x] Spec coverage: the three missing pipeline sections each have a corresponding `_MAIN_SECTIONS` entry.
- [x] No placeholders: every step includes exact code or commands.
- [x] Type consistency: test fixture keys match `_MAIN_SECTIONS` keys.
- [x] DRY: `_MAIN_SECTIONS` is the single source of truth for DOCX and PDF builders.
- [x] YAGNI: no new modules or dependencies beyond pytest for testing.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-28-aegis-template-finish.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks.
2. **Inline Execution** — execute tasks in this session using the executing-plans skill.

Which approach would you like?
