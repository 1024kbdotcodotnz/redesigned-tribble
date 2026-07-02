import re
from typing import Dict, List, Set

from core.fact_sheet import (
    Admission,
    CaseMeta,
    Charge,
    FactSheet,
    ForensicItem,
    OfficerFacts,
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
        sheet.officers = self._extract_officers(raw_text)
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
        # Warrant documents begin with a Section 6 reference. Use those anchors
        # to carve out sections, then collect every SW number inside the
        # section. This avoids matching bare numbers in file/page headers while
        # still merging scope across repeated page-header occurrences.
        section_markers = list(
            re.finditer(
                r"Section 6 of the Search and Surveillance Act",
                text,
                re.IGNORECASE,
            )
        )
        if not section_markers:
            return self._extract_warrants_by_keyword(text, source_name)

        section_starts = [max(0, m.start() - 200) for m in section_markers]
        section_ends = section_starts[1:] + [len(text)]

        # Deduplicate globally across overlapping section windows so a warrant
        # number is emitted only once in the final list.
        by_number: Dict[str, Warrant] = {}
        for sec_start, sec_end in zip(section_starts, section_ends):
            section = text[sec_start:sec_end]
            for m in re.finditer(r"(SW\d+)", section):
                number = m.group(1)
                actual_pos = sec_start + m.start()
                block_start = max(sec_start, actual_pos - 500)
                block_end = min(sec_end, actual_pos + 1500)
                block = text[block_start:block_end]
                line = self._line_for(text, actual_pos)

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

                new_warrant = Warrant(
                    number=number,
                    offence_authorised=offence,
                    scope=scope,
                    place=place,
                    source=f"{source_name}:{line}",
                )

                existing = by_number.get(number)
                if existing is None:
                    by_number[number] = new_warrant
                else:
                    if not existing.offence_authorised:
                        existing.offence_authorised = new_warrant.offence_authorised
                    seen = set(existing.scope)
                    existing.scope.extend(
                        [s for s in new_warrant.scope if s not in seen]
                    )
                    if not existing.place:
                        existing.place = new_warrant.place

        return list(by_number.values())

    def _extract_warrants_by_keyword(
        self, text: str, source_name: str
    ) -> List[Warrant]:
        """Fallback when no explicit Section 6 markers are present."""
        warrants: List[Warrant] = []
        for m in re.finditer(r"(SW\d+)", text):
            number = m.group(1)
            start = max(0, m.start() - 500)
            end = min(len(text), m.end() + 1500)
            block = text[start:end]

            # The number must appear near a warrant keyword.
            window = text[max(0, m.start() - 300) : min(len(text), m.end() + 300)]
            if not re.search(r"\bwarrant\b|section\s+6", window, re.IGNORECASE):
                continue

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
                    source=f"{source_name}:{line}",
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

    def _extract_officers(self, text: str) -> Dict[str, OfficerFacts]:
        officers: Dict[str, OfficerFacts] = {}
        # Trailing header words that should not be captured as part of a name.
        _TRAILERS = r"Statement|Report|Officer|Age|Date|Time|Name"
        patterns = [
            rf"Statement\s+of:\s*([A-Z][a-z]+(?:\s+(?!{_TRAILERS}\b)[A-Z][a-z]+)+)",
            rf"Officer\s+([A-Z][a-z]+(?:\s+(?!{_TRAILERS}\b)[A-Z][a-z]+)+)",
            rf"(?:Constable|Detective|Sergeant)\s+([A-Z][a-z]+(?:\s+(?!{_TRAILERS}\b)[A-Z][a-z]+)+)",
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                name = m.group(1).strip()
                if name and name not in officers:
                    officers[name] = OfficerFacts(name=name)
        return officers

    def _extract_admissions(self, text: str, source_name: str) -> List[Admission]:
        admissions: List[Admission] = []
        seen: Set[str] = set()
        # Look for admission phrases in officer notebook extracts. Keep the
        # inference of `signed` and `lawyer_present` within the same sentence
        # (or logical line) as the admission phrase, rather than a long snippet.
        admission_terms = r"admitted|admission|confessed|declined to comment|refused to sign"
        for m in re.finditer(rf"([^\.\n]*(?:{admission_terms})[^\.\n]*)", text, re.IGNORECASE):
            sentence = m.group(1).strip()
            if not sentence:
                continue
            line = self._line_for(text, m.start())
            sent_lower = sentence.lower()
            signed = self._infer_signed(sent_lower)
            lawyer = None
            if re.search(r"\b(no|not|without)\s+lawyer\b", sent_lower):
                lawyer = False
            elif "lawyer" in sent_lower:
                lawyer = True
            key = re.sub(r"\s+", " ", sent_lower)
            if key in seen:
                continue
            seen.add(key)
            admissions.append(
                Admission(
                    alleged_words=sentence,
                    signed=signed,
                    lawyer_present=lawyer,
                    source=f"{source_name}:{line}",
                )
            )
        return admissions

    def _infer_signed(self, sent_lower: str) -> bool | None:
        """Infer whether a signature was given based on a sentence.

        Returns True only for clear positive signatures, False for explicit
        refusal or negation, and None when ambiguous.
        """
        # Explicit refusal/negation patterns.
        negation_patterns = [
            r"\b(?:refused|declined)\s+to\s+sign\b",
            r"\bnot\s+signed\b",
            r"\bdid\s+not\s+sign\b",
            r"\bnever\s+signed\b",
            r"\bunsigned\b",
            r"\bdidn'?t\s+sign\b",
            r"\bwasn'?t\s+signed\b",
            r"\bweren'?t\s+signed\b",
        ]
        for pattern in negation_patterns:
            if re.search(pattern, sent_lower):
                return False

        # Clear positive signature patterns only.
        positive_patterns = [
            r"\b(?:defendant|he|she|they|suspect|officer|witness|i|we)\s+signed\b",
            r"\bsigned\s+(?:the|a|an|his|her|their|my|our|it|by|and|with)\b",
            r"\b(?:notebook|statement|entry|form|document|page|report|record)\s+(?:was|is|were)\s+signed\b",
            r"\bsigned\s+(?:notebook|statement|entry|form|document|page|report|record)\b",
        ]
        for pattern in positive_patterns:
            if re.search(pattern, sent_lower):
                return True

        return None

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
        text_lower = text.lower()
        for label, term1, term2 in [
            ("body-worn camera footage mentioned or requested", "body", "camera"),
            ("chain-of-custody records", "custody", "record"),
        ]:
            if term1 in text_lower and term2 in text_lower:
                pos = text_lower.find(term1)
                line = self._line_for(text, pos)
                gaps.append(f"{source_name}:{line}: {label}")
        return gaps
