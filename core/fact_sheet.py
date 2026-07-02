from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Charge:
    offence: str = ""
    statute: str = ""


@dataclass
class CaseMeta:
    defendant: str = ""
    charges: List[Charge] = field(default_factory=list)
    court: str = ""
    date: Optional[str] = None


@dataclass
class Quote:
    text: str = ""
    source: str = ""
    context: str = ""


@dataclass
class OfficerFacts:
    name: str = ""
    role: str = ""
    key_quotes: List[Quote] = field(default_factory=list)


@dataclass
class TimelineEvent:
    datetime: Optional[str] = None
    event: str = ""
    source: str = ""
    actor: Optional[str] = None


@dataclass
class Warrant:
    number: str = ""
    offence_authorised: str = ""
    scope: List[str] = field(default_factory=list)
    place: str = ""
    items_seized: List[str] = field(default_factory=list)
    items_not_found: List[str] = field(default_factory=list)
    source: str = ""


@dataclass
class Admission:
    date: Optional[str] = None
    officer: str = ""
    alleged_words: str = ""
    signed: Optional[bool] = None
    lawyer_present: Optional[bool] = None
    context: str = ""
    source: str = ""


@dataclass
class SeizedItem:
    description: str = ""
    location: str = ""
    seized_by: str = ""
    time: Optional[str] = None
    exhibit_number: Optional[str] = None
    source: str = ""


@dataclass
class ForensicItem:
    description: str = ""
    result: str = ""
    analyst: str = ""
    source: str = ""


@dataclass
class FactSheet:
    case_meta: CaseMeta = field(default_factory=CaseMeta)
    warrants: List[Warrant] = field(default_factory=list)
    timeline: List[TimelineEvent] = field(default_factory=list)
    officers: Dict[str, OfficerFacts] = field(default_factory=dict)
    admissions: List[Admission] = field(default_factory=list)
    forensics: List[ForensicItem] = field(default_factory=list)
    seized_items: List[SeizedItem] = field(default_factory=list)
    not_found_items: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        # dataclasses.asdict handles nested dataclasses automatically
        from dataclasses import asdict
        return asdict(self)
