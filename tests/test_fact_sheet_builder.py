import os
from pathlib import Path

import pytest

from core.parser import DisclosureParser
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
