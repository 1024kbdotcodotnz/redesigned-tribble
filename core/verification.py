import re
from typing import Set

from core.fact_sheet import FactSheet


class ReportVerifier:
    """Flag claims in generated report that lack disclosure anchors."""

    def verify(self, report_text: str, sheet: FactSheet) -> str:
        notes = []

        # Known names from fact sheet
        known_names: Set[str] = set()
        for officer in sheet.officers.values():
            known_names.add(officer.name)
            known_names.update(officer.name.split())
        for admission in sheet.admissions:
            if admission.officer:
                known_names.add(admission.officer)

        # Find capitalised names (First Last) in report that are not in fact sheet
        for match in re.finditer(r"[A-Z][a-z]+\s+[A-Z][a-z]+", report_text):
            name = match.group(0)
            if name not in known_names and not self._is_common_word(name):
                notes.append(f"Unverified name: {name}")

        # Find paragraphs without any source marker
        paragraphs = [p.strip() for p in report_text.split("\n") if p.strip()]
        unanchored = 0
        for para in paragraphs:
            if not re.search(r"\(.*\d+.*\)|\[.*\d+.*\]|notebook|statement|line \d+|source:", para, re.IGNORECASE):
                if len(para) > 80:
                    unanchored += 1
        if unanchored:
            notes.append(f"{unanchored} paragraphs lack explicit source anchors")

        if not notes:
            return report_text

        return report_text + "\n\n## VERIFICATION NOTES\n\n" + "\n".join(f"- {n}" for n in notes[:10])

    def _is_common_word(self, name: str) -> bool:
        return name.lower() in {
            "new zealand", "high court", "district court", "supreme court",
            "court of appeal", "evidence act", "crimes act", "search and surveillance",
            "nzbora", "police", "the crown", "section",
        }
