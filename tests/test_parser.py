from core.parser import DisclosureParser


def test_parser_infers_burglary_from_text():
    parser = DisclosureParser()
    text = """
    POLICE v Jordan Michael Harper
    Summary of Facts
    On 14 April 2026 Jordan Harper entered TechHub Electronics as a trespasser
    and stole three laptops and one tablet. Fingerprint evidence was recovered.
    """
    parsed = parser.parse(text)
    assert parsed.primary_charge is not None
    assert parsed.primary_charge["offense"] == "Burglary"
    assert "Crimes Act 1961" in parsed.primary_charge["statute"]


def test_parser_extracts_burglary_focused_text():
    parser = DisclosureParser()
    text = """
    POLICE v Jordan Michael Harper
    Charging Document
    Offence description: Burglary
    Legislative reference: Crimes Act 1961, s 231
    Maximum penalty: 10 years imprisonment

    Summary of Facts
    On 14 April 2026 the defendant entered TechHub Electronics.
    """
    primary = parser._extract_primary_charge(text)
    assert primary is not None
    assert primary["offense"] == "Burglary"
