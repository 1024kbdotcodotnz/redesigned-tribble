from core.parser import DisclosureParser
from core.fact_sheet_builder import FactSheetBuilder


def test_build_warrants_from_lim():
    text = open(
        r"C:/Users/megab/OneDrive/Documents/Disclosure/Lim/adf_scan_ocr_20260323_105350.txt",
        encoding="utf-8",
    ).read()
    parser = DisclosureParser()
    parsed = parser.parse(text)
    builder = FactSheetBuilder()
    sheet = builder.build(parsed, text, source_name="adf_scan_ocr_20260323_105350.txt")
    assert len(sheet.warrants) >= 1
    w = sheet.warrants[0]
    assert "SW392060019347" in w.number
    assert any("trailer" in s.lower() for s in w.scope)
