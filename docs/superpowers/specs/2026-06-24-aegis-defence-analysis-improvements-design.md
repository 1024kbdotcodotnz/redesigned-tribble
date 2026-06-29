# AEGIS Defence Analysis — Reference Output Match

**Date:** 2026-06-24  
**Goal:** Bring AEGIS Defence Analysis output closer to the Kimi reference Word-document legal brief for NZ criminal defence, while adding export capability and regression tests.

## Changes Made

### 1. DOCX export + modular report export (`core/report_export.py`)
- New module `core/report_export.py` with:
  - `build_docx(report)` — produces a formatted Word document from the analysis result dict.
  - `build_html(report)` — produces printable HTML (refactored out of the Streamlit UI).
- Wired into `web/streamlit_app.py` as a second download button next to the existing HTML Save/Print button.
- Added primary-button styling for the new DOCX download in `web/theme.css`.

### 2. Output quality fixes (`core/prompts.py`, `core/agent_swarm.py`)
- Hardened prompts and post-processing to enforce **actual knowledge** for Misuse of Drugs Act 1975 s 7(1)(a) possession — stripped "ought reasonably to have known", "should have known", and "constructive knowledge".
- Replaced literal `[Today's Date]` placeholders with the actual date.
- Improved court extraction in the parser and title-block fallback.
- Enforced `A.`, `B.`, `C.` labels on defence strategies.
- Improved fallback titles for first Disclosure Gap and first Evidentiary Issue.
- Forced numbered formatting under `## Weaknesses`.
- Sharpened cross-examination prompt to focus on warning/inducement, legal advice, unsigned notebook, and warrantless-search authority.

### 3. Parser robustness (`core/parser.py`)
- Added `court` field to `ParsedDisclosure` and `to_dict` output.
- Fixed case-title and defendant-name regexes to avoid swallowing newlines.
- Expanded offence-description regex to handle commas and common punctuation.

### 4. Regression tests (`test_pipeline.py`)
- Added `GBL_DISCLOSURE` and `BURGLARY_THEFT_DISCLOSURE` fixtures.
- Added parser and stub-pipeline tests for both case types.
- Fixed pre-existing assertion that expected `flags` in `to_dict` output.

### 5. UI bug fix (`web/streamlit_app.py`)
- Fixed auto-scroll JavaScript that referenced an undefined `headings[i]` variable.

## Files Touched
- `core/report_export.py` (new)
- `core/prompts.py`
- `core/agent_swarm.py`
- `core/parser.py`
- `web/streamlit_app.py`
- `web/theme.css`
- `test_pipeline.py`

## Verification
- `python -m py_compile` passed for all modified Python files.
- `python test_pipeline.py` (stub tests only) passed.
- HTML export tested locally. DOCX export requires `python-docx` (already in `requirements.txt`); local environment lacked it, but the code degrades gracefully with a caption message.

## Next Steps (user-side)
1. Upload changed files to RunPod `d5a059f701d8`.
2. Restart the AEGIS services.
3. Run the live GBL analysis and verify:
   - Title block shows correct court and date.
   - Elements use **actual knowledge** only.
   - Defence strategies have `A.`, `B.`, `C.` labels.
   - Cross-examination questions are fact-specific.
   - DOCX download works.
4. Run burglary/theft analysis and confirm charge/framework accuracy.
