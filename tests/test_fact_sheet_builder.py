import os
from pathlib import Path

import pytest

from core.parser import DisclosureParser, ParsedDisclosure
from core.fact_sheet_builder import FactSheetBuilder


LIM_FILE = "adf_scan_ocr_20260323_105350.txt"


def _lim_file_path() -> Path:
    override = os.environ.get("DISCLOSURE_LIM_DIR")
    if override:
        return Path(override) / LIM_FILE
    return Path.home() / "OneDrive" / "Documents" / "Disclosure" / "Lim" / LIM_FILE


def test_build_warrants_from_lim():
    file_path = _lim_file_path()
    if not file_path.exists():
        pytest.skip(f"Disclosure Lim file not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    parser = DisclosureParser()
    parsed = parser.parse(text)
    builder = FactSheetBuilder()
    sheet = builder.build(parsed, text, source_name=LIM_FILE)
    assert len(sheet.warrants) >= 1
    w = sheet.warrants[0]
    assert "SW392060019347" in w.number
    assert any("trailer" in s.lower() for s in w.scope)


# Synthetic unit tests for extraction logic (do not rely on external disclosure files).


def _minimal_parsed() -> ParsedDisclosure:
    return ParsedDisclosure(
        defendant={"name": "Synthetic Defendant"},
        charges=[{"offence": "Theft", "statute": "Crimes Act 1961, s 234"}],
        court="District Court",
    )


def test_warrant_section_extraction_and_deduplication():
    snippet = """\
Section 6 of the Search and Surveillance Act 2012

Warrant to search a place at 123 Main Street
offence of: Theft
- trailer
- winch
SW123456789012

Section 6 of the Search and Surveillance Act 2012

Warrant to search a place at 456 High Street
offence of: Burglary
- labels
- stickers
SW123456789012
"""
    builder = FactSheetBuilder()
    sheet = builder.build(_minimal_parsed(), snippet, source_name="synthetic.txt")
    # Same warrant number repeated in overlapping sections should be emitted once.
    assert len(sheet.warrants) == 1
    assert sheet.warrants[0].number == "SW123456789012"
    scope = [s.lower() for s in sheet.warrants[0].scope]
    assert "trailer" in scope
    assert "labels" in scope


def test_warrant_fallback_by_keyword():
    # The keyword fallback requires an SW number to appear within ~300 chars of
    # a warrant keyword. Keep the second number well outside that window and
    # avoid the word "warrant" in the surrounding text.
    filler = "\n".join([f"Line {i} has no relevant police terminology." for i in range(20)])
    snippet = f"""\
Pursuant to a search warrant.
Some earlier page header SW999988887777
{filler}
No matching authority language around here SW000011112222
"""
    builder = FactSheetBuilder()
    sheet = builder.build(_minimal_parsed(), snippet, source_name="fallback.txt")
    # Only the number near a warrant keyword should be kept.
    numbers = [w.number for w in sheet.warrants]
    assert "SW999988887777" in numbers
    assert "SW000011112222" not in numbers


def test_admission_sentence_level_extraction():
    snippet = """\
The defendant admitted the offending.
A lawyer was present. The notebook was signed.
He later refused to sign another statement.
"""
    builder = FactSheetBuilder()
    sheet = builder.build(_minimal_parsed(), snippet, source_name="admissions.txt")
    assert len(sheet.admissions) == 2
    texts = [a.alleged_words.lower() for a in sheet.admissions]
    assert any("admitted" in t for t in texts)
    assert any("refused to sign" in t for t in texts)
    refused = next(a for a in sheet.admissions if "refused" in a.alleged_words.lower())
    assert refused.signed is False


def test_lim_officers_and_admission():
    file_path = _lim_file_path()
    if not file_path.exists():
        pytest.skip(f"Disclosure Lim file not found: {file_path}")

    text = file_path.read_text(encoding="utf-8")
    parser = DisclosureParser()
    parsed = parser.parse(text)
    builder = FactSheetBuilder()
    sheet = builder.build(parsed, text, source_name=LIM_FILE)
    names = {o.name for o in sheet.officers.values()}
    assert "Adeeb Althaf" in names or "Alyssa Marie Booth" in names or "Taylor Ashby" in names
    assert any("admitted" in a.alleged_words.lower() for a in sheet.admissions)
    assert any("refused to sign" in a.alleged_words.lower() for a in sheet.admissions)


def test_gap_labels_include_line_anchor():
    snippet = """\
First line.
Second line mentions body-worn camera footage.
Third line.
Fourth line refers to custody records.
"""
    builder = FactSheetBuilder()
    sheet = builder.build(_minimal_parsed(), snippet, source_name="gaps.txt")
    assert len(sheet.gaps) == 2
    assert all(g.startswith("gaps.txt:") for g in sheet.gaps)
    assert any("body-worn camera" in g for g in sheet.gaps)
    assert any("chain-of-custody" in g for g in sheet.gaps)
