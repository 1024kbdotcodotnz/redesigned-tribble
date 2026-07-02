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
