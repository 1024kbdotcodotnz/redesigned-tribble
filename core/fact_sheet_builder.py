import re
from typing import Any, Dict, List, Optional

from core.fact_sheet import (
    Admission,
    CaseMeta,
    Charge,
    FactSheet,
    ForensicItem,
    OfficerFacts,
    Quote,
    SeizedItem,
    TimelineEvent,
    Warrant,
)
from core.parser import ParsedDisclosure


class FactSheetBuilder:
    """Build a source-anchored fact sheet from parsed disclosure and raw text."""

    def build(
        self,
        parsed: ParsedDisclosure,
        raw_text: str,
        source_name: str = "disclosure.txt",
    ) -> FactSheet:
        sheet = FactSheet()
        sheet.case_meta = self._build_case_meta(parsed)
        sheet.warrants = self._extract_warrants(raw_text, source_name)
        sheet.timeline = self._extract_timeline(raw_text, source_name)
        sheet.officers = self._extract_officers(raw_text, source_name)
        sheet.admissions = self._extract_admissions(raw_text, source_name)
        sheet.forensics = self._extract_forensics(raw_text, source_name)
        sheet.seized_items = self._extract_seized_items(raw_text, source_name)
        sheet.not_found_items = self._extract_not_found_items(raw_text, source_name)
        sheet.gaps = self._extract_gaps(raw_text, source_name)
        return sheet

    def _build_case_meta(self, parsed: ParsedDisclosure) -> CaseMeta:
        charges = []
        for c in parsed.charges or []:
            charges.append(
                Charge(
                    offence=c.get("offence", ""),
                    statute=c.get("statute", ""),
                )
            )
        if not charges and parsed.primary_charge:
            charges.append(
                Charge(
                    offence=parsed.primary_charge.get("offence", ""),
                    statute=parsed.primary_charge.get("statute", ""),
                )
            )
        return CaseMeta(
            defendant=parsed.defendant.get("name") or "",
            charges=charges,
            court=parsed.court or "",
        )

    def _line_for(self, raw_text: str, pos: int) -> int:
        return raw_text[:pos].count("\n") + 1

    def _extract_warrants(self, text: str, source_name: str) -> List[Warrant]:
        warrants = []
        # Find warrant blocks by number pattern SW\d+
        for m in re.finditer(r"(SW\d+)", text):
            number = m.group(1)
            start = max(0, m.start() - 500)
            end = min(len(text), m.end() + 1500)
            block = text[start:end]
            line = self._line_for(text, m.start())

            offence = ""
            offence_m = re.search(
                r"offence of\s*[:]?\s*([^\n]+(?:\n[^\n]{0,200})?)",
                block,
                re.IGNORECASE,
            )
            if offence_m:
                offence = re.sub(r"\s+", " ", offence_m.group(1)).strip()

            scope = []
            for bullet in re.finditer(r"^\s*[-•*]\s*(.+)$", block, re.MULTILINE):
                scope.append(bullet.group(1).strip())

            place = ""
            place_m = re.search(
                r"(?:search|warrant to search)\s+a\s+(?:place|vehicle|address)[,\s]+([^\n]+)",
                block,
                re.IGNORECASE,
            )
            if place_m:
                place = place_m.group(1).strip()

            warrants.append(
                Warrant(
                    number=number,
                    offence_authorised=offence,
                    scope=scope,
                    place=place,
                )
            )

        # Merge duplicate warrant numbers (e.g., page-header reprints) so the
        # first entry captures the full scope.
        by_number: Dict[str, Warrant] = {}
        for w in warrants:
            existing = by_number.get(w.number)
            if existing is None:
                by_number[w.number] = w
            else:
                if not existing.offence_authorised:
                    existing.offence_authorised = w.offence_authorised
                seen = set(existing.scope)
                existing.scope.extend([s for s in w.scope if s not in seen])
                if not existing.place:
                    existing.place = w.place
        return list(by_number.values())

    def _extract_timeline(self, text: str, source_name: str) -> List[TimelineEvent]:
        events = []
        # time-stamped events like "15/11/2025 10:41" or "About 10:41am"
        pattern = re.compile(
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?\s*(About\s+)?(\d{1,2}[:\.]\d{2})\s*(am|pm)?[\s\-]*(.{0,200})",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            date_part = m.group(1) or ""
            time_part = m.group(3) or ""
            ampm = m.group(4) or ""
            desc = m.group(5).strip()
            if not desc:
                continue
            line = self._line_for(text, m.start())
            events.append(
                TimelineEvent(
                    datetime=f"{date_part} {time_part}{ampm}".strip(),
                    event=re.sub(r"\s+", " ", desc),
                    source=f"{source_name}:{line}",
                )
            )
        return events

    def _extract_officers(self, text: str, source_name: str) -> Dict[str, OfficerFacts]:
        officers: Dict[str, OfficerFacts] = {}
        # Match "Statement of: First Last" blocks
        for m in re.finditer(r"Statement\s+of:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", text):
            name = m.group(1).strip()
            if name not in officers:
                officers[name] = OfficerFacts(name=name)
        return officers

    def _extract_admissions(self, text: str, source_name: str) -> List[Admission]:
        admissions = []
        # Look for admission phrases in officer notebook extracts
        for m in re.finditer(
            r"((?:admitted|admission|confessed|declined to comment|refused to sign)[^\n]{0,500})",
            text,
            re.IGNORECASE,
        ):
            snippet = m.group(1).strip()
            line = self._line_for(text, m.start())
            signed = None
            if "refused to sign" in snippet.lower():
                signed = False
            elif "signed" in snippet.lower() and "refused" not in snippet.lower():
                signed = True
            lawyer = None
            if "lawyer" in snippet.lower():
                lawyer = True
            admissions.append(
                Admission(
                    alleged_words=snippet,
                    signed=signed,
                    lawyer_present=lawyer,
                    source=f"{source_name}:{line}",
                )
            )
        return admissions

    def _extract_forensics(self, text: str, source_name: str) -> List[ForensicItem]:
        forensics = []
        for m in re.finditer(
            r"((?:identified|confirmed|tested|results?)[^\n]{0,200}(?:GBL|gamma|methamphetamine|cannabis|class\s+[bB])[^\n]{0,200})",
            text,
            re.IGNORECASE,
        ):
            line = self._line_for(text, m.start())
            forensics.append(
                ForensicItem(
                    description=m.group(1).strip(),
                    result="",
                    analyst="",
                    source=f"{source_name}:{line}",
                )
            )
        return forensics

    def _extract_seized_items(self, text: str, source_name: str) -> List[SeizedItem]:
        items = []
        pattern = re.compile(
            r"(?:about\s+)?(\d{1,2}[:\.]\d{2}\s*(?:am|pm))?\s*I\s+seized\s+([^\n]{0,200})",
            re.IGNORECASE,
        )
        for m in pattern.finditer(text):
            line = self._line_for(text, m.start())
            items.append(
                SeizedItem(
                    description=m.group(2).strip(),
                    location="",
                    seized_by="",
                    time=m.group(1),
                    source=f"{source_name}:{line}",
                )
            )
        return items

    def _extract_not_found_items(self, text: str, source_name: str) -> List[str]:
        not_found = []
        for m in re.finditer(r"((?:no|not)\s+(?:trailer|labels|winch|stickers)[^\n]{0,150})", text, re.IGNORECASE):
            line = self._line_for(text, m.start())
            not_found.append(f"{m.group(1).strip()} ({source_name}:{line})")
        return not_found

    def _extract_gaps(self, text: str, source_name: str) -> List[str]:
        gaps = []
        if "body" in text.lower() and "camera" in text.lower():
            gaps.append("Body-worn camera footage mentioned or requested")
        if "custody" in text.lower() and "record" in text.lower():
            gaps.append("Chain-of-custody records")
        return gaps
