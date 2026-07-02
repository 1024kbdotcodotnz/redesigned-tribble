from core.fact_sheet import FactSheet, CaseMeta, Charge, Warrant


def test_fact_sheet_instantiation():
    fs = FactSheet(
        case_meta=CaseMeta(
            defendant="James Lim",
            charges=[Charge(offence="Possess Class B drug", statute="s 7(1)(a) Misuse of Drugs Act 1975")],
            court="Pukekohe District Court",
        ),
        warrants=[
            Warrant(
                number="SW392060019347-617",
                offence_authorised="Receives Property",
                scope=["trailer 645C2 labels"],
                place="23 Logan Road, Buckland",
            )
        ],
    )
    assert fs.case_meta.defendant == "James Lim"
    assert fs.warrants[0].number == "SW392060019347-617"
