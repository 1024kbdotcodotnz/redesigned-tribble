from core.fact_sheet import FactSheet, OfficerFacts
from core.verification import ReportVerifier


def test_flags_unanchored_claim():
    verifier = ReportVerifier()
    sheet = FactSheet()
    sheet.officers["Taylor Ashby"] = OfficerFacts(name="Taylor Ashby", role="OIC")
    text = "Officer Smith invented this fact. Taylor Ashby observed the trailer."
    result = verifier.verify(text, sheet)
    assert "Smith" in result or "unanchored" in result.lower()
