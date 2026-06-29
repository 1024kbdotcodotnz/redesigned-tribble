# AEGIS Defence Analysis Report Template Redesign

## Overview
Redesign the DOCX and PDF export templates for AEGIS defence analysis briefs so that every page carries the AEGIS brand, sections are formatted uniformly, and no section or sub-section splits across a page boundary.

## Goals
- Embed the AEGIS brand (`⚖️ AEGIS ⚖️`) at the top of every exported page.
- Keep main sections and their sub-sections visually together; insert page breaks only when content would otherwise overflow the current page.
- Make DOCX and PDF output share identical visual rules (fonts, spacing, indentation, heading hierarchy, legal-basis formatting).
- Preserve the existing fallback PDF renderer so exports still work when Microsoft Word / docx2pdf is unavailable.

## Design Decisions

### Brand Header
- **Logo mark:** Text-based `⚖️ AEGIS ⚖️` (scales on both sides).
- **Style:** "Professional Rule" — centred at the top of every page.
- **Colours:**
  - Brand text: dark blue `#2c3e50`
  - Accent rule: gold/bronze `#c5a880`
  - Separator below header: `#2c3e50` (dark blue) 1 pt rule
- **Tagline:** `NZ's Legal Adviser · Secure Legal Research` in small uppercase tracking below the mark.

### Typography
- **Body text:** 12 pt Calibri (DOCX) / Calibri when available, otherwise Helvetica (PDF fallback), colour `#1d1d1f`.
- **Heading hierarchy (clean sans-serif):**
  - Main section heading (`1. EXECUTIVE SUMMARY`): 16 pt bold, `#2c3e50`, small space below.
  - Level-2 heading (`## ...`): 14 pt bold, `#34495e`.
  - Level-3 heading (`### ...`): 13 pt bold, `#34495e`.
  - Level-4 heading (`#### ...`): 12 pt bold, `#34495e`.
- **Line spacing:** ~1.5 for body paragraphs; 6 pt after paragraphs, 12 pt after headings.

### Footer
- Appears on every page including the title page.
- Three columns:
  - Left: `Confidential Defence Analysis`
  - Centre: `Prepared: <date>`
  - Right: `Page <n>`
- Font: 9 pt, grey `#666666`.

### Page-Break Rules
- A **main section** is the block from its level-1 heading through to the next level-1 heading.
- A **sub-section** is the block from a `##`/`###`/`####` heading through to the next heading of any level.
- Use Word paragraph formatting to keep these units together:
  - `paragraph_format.keep_together = True` on every paragraph in a section/sub-section.
  - `paragraph_format.keep_with_next = True` on each heading and on all paragraphs except the last in the unit.
- This lets Word decide dynamically whether the unit fits on the current page; if not, it moves the whole unit to the next page.
- If a unit is longer than one full page, Word is allowed to break it at a paragraph boundary (keep_together prevents mid-paragraph splits).

### Uniform Section Formatting
- **Headings:** Numbered sequentially (`1.`, `2.`, etc.) for main sections only. Sub-sections keep their markdown heading text without added numbering.
- **Legal Basis lines:** Normalised to the form `Legal Basis: <citation>`.
- **Numbered lists:** `1. Item` with hanging indent; continuation lines indented to align with the item text.
- **Bullet lists:** `• Item`, indented 0.25 in from left margin; continuation lines aligned.
- **Bold labels:** `Key finding:` or `**Label:**` rendered as bold label followed by normal body text.
- **Statute citations:** Bare citations (e.g. `Crimes Act 1961, s 234`) promoted to `Legal Basis: Crimes Act 1961, s 234`.

### DOCX Implementation
- Load `data/templates/defence_analysis.docx` if it exists; otherwise create a blank document.
- Set `Normal` style to Calibri 12 pt.
- Configure document section margins and header/footer via `doc.sections[0]`.
- Add the brand header to the section header so it repeats on every page.
- Add the footer to the section footer so it repeats on every page.
- Build the title page, then Table of Contents, then main sections.
- Apply keep-together/keep-with-next logic during content insertion.

### PDF Implementation
- **Primary path:** `build_docx()` → save to temp DOCX → `docx2pdf.convert()` → PDF.
  - This guarantees PDF matches DOCX exactly, including headers, footers, and dynamic page breaks.
- **Fallback path:** `_build_pdf_with_fpdf()` using fpdf2.
  - Replicate the same header/footer by drawing them manually on each page.
  - Replicate the same content formatting (fonts, sizes, indentation, legal-basis normalisation).
  - Page-break handling is simpler in fpdf2: we can only force page breaks explicitly; we will add a page break before each main section and sub-section to mirror the "keep unbroken" intent.

## Files to Modify
- `aegis/core/report_export.py` — primary export builder.
- `aegis/data/templates/defence_analysis.docx` — optional Word template.
- `aegis/requirements.txt` — already includes `python-docx`, `fpdf2`, `docx2pdf`.

## Testing / Verification
- Generate a DOCX and PDF from the existing test pipeline output.
- Verify header appears on every page.
- Verify footer shows brand, date, and page number.
- Check that main section headings do not appear alone at the bottom of a page.
- Confirm fonts, indentation, and legal-basis formatting are consistent between DOCX and PDF.
- Confirm fallback fpdf2 path still produces a readable PDF if docx2pdf is unavailable.

## Out of Scope
- Adding a real image/logo file (using text mark only).
- Changing the analysis content produced by the LLM pipeline.
- Adding a cover page beyond the existing title page.

## Approval
Approved by user with the change: body text set to 12 pt.
