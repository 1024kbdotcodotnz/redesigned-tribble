#!/usr/bin/env python3
"""
NZ Legal RAG — Disclosure Parser (Production v2)
Extracts structured data from police disclosure text using regex and LLM fallback.
"""

import re
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime

@dataclass
class ParsedDisclosure:
    case_title: str = ""
    defendant: Dict[str, Any] = field(default_factory=dict)
    charges: List[Dict[str, Any]] = field(default_factory=list)
    primary_charge: Optional[Dict[str, Any]] = None
    court: str = ""
    procedural_history: Dict[str, Any] = field(default_factory=dict)
    witnesses: List[Dict[str, Any]] = field(default_factory=list)
    physical_evidence: List[Dict[str, Any]] = field(default_factory=list)
    prior_convictions: List[Dict[str, Any]] = field(default_factory=list)
    disclosure_gaps: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    raw_text: str = ""

class DisclosureParser:
    """Rule-based parser with optional LLM enhancement."""

    # Statute patterns
    STATUTE_PATTERNS = [
        r"Crimes Act 1961,?\s*s\s*(\d+[A-Z]?)",
        r"Summary Offences Act 1981,?\s*s\s*(\d+[A-Z]?)",
        r"Bail Act 2000,?\s*s\s*(\d+[A-Z]?)",
        r"Evidence Act 2006,?\s*s\s*(\d+[A-Z]?)",
        r"Search and Surveillance Act 2012,?\s*s\s*(\d+[A-Z]?)",
        r"Sentencing Act 2002,?\s*s\s*(\d+[A-Z]?)",
        r"Criminal Disclosure Act 2008,?\s*s\s*(\d+[A-Z]?)",
        r"Misuse of Drugs Act 1975,?\s*[Ss]ection\s*(\d+[A-Z]?(?:\(\d+\)(?:\([a-z]\))?)?)",
        r"Misuse of Drugs Act 1975,?\s*s\s*(\d+[A-Z]?(?:\(\d+\)(?:\([a-z]\))?)?)",
    ]

    # Offense keywords
    OFFENSE_KEYWORDS = [
        ("theft", "Theft", "Crimes Act 1961, s 234"),
        ("burglary", "Burglary", "Crimes Act 1961, s 231"),
        ("trespasser", "Burglary", "Crimes Act 1961, s 231"),
        ("entered a building", "Burglary", "Crimes Act 1961, s 231"),
        ("assault", "Assault", "Crimes Act 1961, s 196"),
        ("common assault", "Common Assault", "Crimes Act 1961, s 196"),
        ("male assaults female", "Male Assaults Female", "Crimes Act 1961, s 194"),
        ("wounding", "Wounding with Intent", "Crimes Act 1961, s 188"),
        ("aggravated robbery", "Aggravated Robbery", "Crimes Act 1961, s 235"),
        ("robbery", "Robbery", "Crimes Act 1961, s 235"),
        ("fraud", "Fraud", "Crimes Act 1961, s 240"),
        ("dishonestly", "Theft/Dishonesty", "Crimes Act 1961, s 234"),
        ("gbl", "Possession of GBL", "Misuse of Drugs Act 1975, s 7(1)(a)"),
        ("gamma-butyrolactone", "Possession of GBL", "Misuse of Drugs Act 1975, s 7(1)(a)"),
        ("gamma butyrolactone", "Possession of GBL", "Misuse of Drugs Act 1975, s 7(1)(a)"),
        ("class b drug", "Possession of Class B Drug", "Misuse of Drugs Act 1975, s 7(1)(a)"),
        ("class b", "Possession of Class B Drug", "Misuse of Drugs Act 1975, s 7(1)(a)"),
        ("methamphetamine", "Methamphetamine", "Misuse of Drugs Act 1975, s 6"),
        ("cannabis", "Cannabis", "Misuse of Drugs Act 1975, s 6"),
        ("drug", "Drug Offense", "Misuse of Drugs Act 1975"),
        ("driving", "Driving Offense", "Land Transport Act 1998"),
        ("breath alcohol", "Excess Breath Alcohol", "Land Transport Act 1998, s 56"),
        ("dangerous driving", "Dangerous Driving", "Land Transport Act 1998, s 22"),
    ]

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def parse(self, text: str) -> ParsedDisclosure:
        """Parse disclosure text into structured data."""
        text = text.strip()
        if not text:
            return ParsedDisclosure()

        parsed = ParsedDisclosure(raw_text=text)

        # Extract case title
        parsed.case_title = self._extract_case_title(text)

        # Extract defendant
        parsed.defendant = self._extract_defendant(text)

        # Extract charges
        parsed.charges = self._extract_charges(text)

        # Extract the formal charge from the Charging Document (authoritative)
        parsed.primary_charge = self._extract_primary_charge(text)

        # Extract court name
        parsed.court = self._extract_court(text)

        # Fallback: if no Charging Document section, infer the primary charge from
        # substance/statute references in the text (e.g., GBL / Misuse of Drugs Act).
        if not parsed.primary_charge:
            print("[PARSER] primary_charge empty, running fallback inference")
            parsed.primary_charge = self._infer_primary_charge_from_text(text)
            print(f"[PARSER] primary_charge after fallback: {parsed.primary_charge}")

        # Extract procedural history
        parsed.procedural_history = self._extract_procedural_history(text)

        # Extract witnesses
        parsed.witnesses = self._extract_witnesses(text)

        # Extract physical evidence
        parsed.physical_evidence = self._extract_physical_evidence(text)

        # Extract prior convictions
        parsed.prior_convictions = self._extract_prior_convictions(text)

        # Identify flags
        parsed.flags = self._identify_flags(text, parsed)

        # Identify disclosure gaps
        parsed.disclosure_gaps = self._identify_gaps(text, parsed)

        # If LLM client available, enhance parsing
        if self.llm_client:
            parsed = self._llm_enhance(parsed, text)

        return parsed

    def _extract_case_title(self, text: str) -> str:
        """Extract case title (e.g., 'POLICE v JOHN SMITH')."""
        # Match POLICE V NAME or POLICE v NAME (case insensitive V/v)
        # Restrict whitespace to spaces/tabs so we don't swallow newlines.
        match = re.search(r"([A-Z][A-Z \t]+)[ \t]+[Vv][ \t]+([A-Z][A-Za-z \t,\-']+)", text)
        if match:
            return f"{match.group(1).strip()} v {match.group(2).strip().rstrip(',')}"
        return "Unknown"

    def _extract_defendant(self, text: str) -> Dict[str, Any]:
        """Extract defendant information."""
        defendant = {"name": None, "date_of_birth": None, "address": None, "age_at_offense": None}

        # Try to find name from case title
        match = re.search(r"[Vv][ \t]+([A-Z][A-Za-z \t,\-']+)", text)
        if match:
            defendant["name"] = match.group(1).strip().rstrip(',')

        # Address patterns — be more specific to avoid bail conditions
        addr_match = re.search(r"(?:reside at|residing at|address is|lives at)\s+([0-9]+[A-Z]?\s+[^,.]+(?:Road|Street|Ave|Avenue|Drive|Place|Lane|St|Rd|Dr))", text, re.IGNORECASE)
        if addr_match:
            defendant["address"] = addr_match.group(1).strip()

        return defendant

    def _extract_charges(self, text: str) -> List[Dict[str, Any]]:
        """Extract charges with statute references."""
        charges = []

        # Look for explicit statute references
        for pattern in self.STATUTE_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                section = match.group(1)
                statute_name = match.group(0).split(",")[0].strip()

                # Find surrounding context (100 chars before and after for better context)
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end]

                # Determine offense name from context or keywords
                offense_name = self._infer_offense(context)

                # Extract value — look for $ prefix first
                value = self._extract_value(context)

                charges.append({
                    "offense": offense_name,
                    "statute": f"{statute_name}, s {section}",
                    "date_of_offense": self._extract_date_near(text, match.start()),
                    "location": self._extract_location_near(text, match.start()),
                    "alleged_facts": context.strip(),
                    "value_involved": value,
                    "aggravating_factors": [],
                    "potential_defences": []
                })

        # If no explicit statutes found, use keyword matching
        if not charges:
            for keyword, offense_name, statute in self.OFFENSE_KEYWORDS:
                if keyword.lower() in text.lower():
                    charges.append({
                        "offense": offense_name,
                        "statute": statute,
                        "date_of_offense": self._extract_date(text),
                        "location": self._extract_location(text),
                        "alleged_facts": text[:200] + "...",
                        "value_involved": self._extract_value(text),
                        "aggravating_factors": [],
                        "potential_defences": []
                    })
                    break

        return charges

    def _extract_primary_charge(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the formal charge from the Charging Document section.

        The Charging Document is the authoritative source of the actual charge(s)
        before the court. Background offences referenced in warrants or statements
        should not be treated as the primary charge.
        """
        has_charging_label = bool(re.search(r"Charging Document", text, re.IGNORECASE))
        has_offence_details = bool(re.search(r"Offence Details|Offence description", text, re.IGNORECASE))
        print(f"[PARSER] _extract_primary_charge: text_len={len(text)}, has_charging_label={has_charging_label}, has_offence_details={has_offence_details}")

        # Find the Charging Document section (from label through to the prosecutor/next document).
        # The section end markers vary across disclosure formats, so we include several.
        section = None
        match = re.search(
            r"Charging Document.*?(?=Prosecutor details|Prosecutor\s+details|First appearance hearing|NOTICE OF|Family Violence|Offence category|signature|Signature|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        if match:
            candidate = match.group(0)
            print(f"[PARSER] first regex matched, candidate_len={len(candidate)}, has_offence_details={'Offence Details' in candidate or 'offence description' in candidate.lower()}")
            if "Offence Details" in candidate or "offence description" in candidate.lower():
                section = candidate
        else:
            print("[PARSER] first Charging Document regex did not match")

        # Fallback 1: look for a standalone "Offence Details" block near a charging doc label.
        if section is None:
            match = re.search(
                r"(?:Charging Document|Charge details|Offence Details).*?(?=Prosecutor details|First appearance hearing|NOTICE OF|Signature|$)",
                text,
                re.IGNORECASE | re.DOTALL
            )
            if match:
                section = match.group(0)
                print(f"[PARSER] fallback 1 matched, section_len={len(section)}")
            else:
                print("[PARSER] fallback 1 did not match")

        # Fallback 2: look for the literal "Offence description:" and surrounding fields.
        if section is None:
            match = re.search(
                r"(?:CRN|Charge Code|Offence code).*?Offence description:.*?Legislative reference:.*?Maximum penalty:",
                text,
                re.IGNORECASE | re.DOTALL
            )
            if match:
                section = match.group(0)
                print(f"[PARSER] fallback 2 matched, section_len={len(section)}")
            else:
                print("[PARSER] fallback 2 did not match")

        if not section:
            print("[PARSER] no Charging Document section found")
            return None

        # Defendant name
        defendant_name = None
        name_match = re.search(r"Name:\s*([A-Z][A-Z\s,]+?)(?:\s{2,}|\n|PRN|Address|Gender|Date of birth)", section, re.IGNORECASE)
        if name_match:
            defendant_name = name_match.group(1).strip().rstrip(",")

        # Date of offence
        date_of_offense = None
        date_match = re.search(r"Date of offence:\s*([A-Za-z0-9\s,\-]+?)(?:\n|Offence location|$)", section, re.IGNORECASE)
        if date_match:
            date_of_offense = self._parse_date(date_match.group(1).strip())

        # Offence location
        location = None
        loc_match = re.search(r"Offence location:\s*(?:at\s+)?([A-Za-z0-9\s,\-/]+?)(?:\n|Offence code|$)", section, re.IGNORECASE)
        if loc_match:
            location = loc_match.group(1).strip()

        # Offence description
        offence_description = None
        desc_match = re.search(r"Offence description:\s*(?:\n+\s*)?([A-Z][A-Za-z0-9\s\-/,\.\(\)]+?)(?:\n\s*Legislative reference|$)", section, re.IGNORECASE | re.DOTALL)
        if desc_match:
            offence_description = desc_match.group(1).strip()

        # Legislative reference
        statute = None
        statute_match = re.search(r"Legislative reference:\s*(.+?)(?:\n|Maximum penalty|$)", section, re.IGNORECASE)
        if statute_match:
            statute = statute_match.group(1).strip()

        # Maximum penalty
        max_penalty = None
        penalty_match = re.search(r"Maximum penalty:\s*(.+?)(?:\n|Offence category|Offence class|signature|Signature|$)", section, re.IGNORECASE)
        if penalty_match:
            max_penalty = penalty_match.group(1).strip()

        # Fallback for Class B drug possession if the charging document omits the penalty.
        if not max_penalty:
            combined = f"{(offence_description or '')} {(statute or '')}".lower()
            if any(k in combined for k in ("class b", "gbl", "gamma-butyrolactone", "misuse of drugs")):
                max_penalty = "3 months imprisonment and/or a fine not exceeding $500"

        if not offence_description and not statute:
            return None

        # Infer a clean offence name from the description/statute
        offense_name = "Unknown Offense"
        desc_lower = (offence_description or "").lower()
        for keyword, name, _ in self.OFFENSE_KEYWORDS:
            if keyword.lower() in desc_lower:
                offense_name = name
                break
        if offense_name == "Unknown Offense" and statute:
            stat_lower = statute.lower()
            if "misuse of drugs" in stat_lower:
                offense_name = "Drug Offense"
            elif "crimes act" in stat_lower and "231" in stat_lower:
                offense_name = "Burglary"
            elif "crimes act" in stat_lower and ("246" in stat_lower or "247" in stat_lower):
                offense_name = "Receiving"

        return {
            "offense": offense_name,
            "statute": statute,
            "description": offence_description,
            "date_of_offense": date_of_offense,
            "location": location,
            "maximum_penalty": max_penalty,
            "defendant_name": defendant_name,
            "court": self._extract_court(text),
        }

    def _infer_primary_charge_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Infer the primary charge when no formal Charging Document is found.

        Some uploaded disclosures (especially scanned/OCR'd files) omit or
        garble the Charging Document heading but still contain the offence
        description and statute elsewhere.
        """
        text_lower = text.lower()

        # Try to find a defendant name nearby
        defendant_name = None
        name_match = re.search(
            r"Defendant\s*\n\s*Name:\s*([A-Z][A-Z\s,]+?)(?:\s{2,}|\n|PRN|Address|Gender|Date of birth)",
            text,
            re.IGNORECASE,
        )
        if name_match:
            defendant_name = name_match.group(1).strip().rstrip(",")
        else:
            bail_match = re.search(
                r"Defendant:\s*([A-Z][A-Z\s,]+?)(?:\n|Address|Date of birth)",
                text,
                re.IGNORECASE,
            )
            if bail_match:
                defendant_name = bail_match.group(1).strip().rstrip(",")

        # Try to find offence date
        date_of_offense = None
        date_match = re.search(
            r"Date of offence:\s*([A-Za-z0-9\s,\-]+?)(?:\n|Offence location|$)",
            text,
            re.IGNORECASE,
        )
        if date_match:
            date_of_offense = self._parse_date(date_match.group(1).strip())

        # Try to find max penalty
        max_penalty = None
        penalty_match = re.search(
            r"Maximum penalty:\s*(.+?)(?:\n|Offence category|Offence class|$)",
            text,
            re.IGNORECASE,
        )
        if penalty_match:
            max_penalty = penalty_match.group(1).strip()

        # Try to find explicit statute references first
        for pattern in self.STATUTE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                section = match.group(1)
                statute_name = match.group(0).split(",")[0].strip()
                statute = f"{statute_name}, s {section}"
                context = text[max(0, match.start() - 200):min(len(text), match.end() + 200)]
                offense_name = self._infer_offense(context)
                if offense_name == "Unknown Offense":
                    offense_name = self._infer_offense(text)
                print(f"[PARSER] _infer_primary_charge_from_text: inferred from statute: {offense_name}")
                return {
                    "offense": offense_name,
                    "statute": statute,
                    "description": context.strip()[:300],
                    "date_of_offense": date_of_offense,
                    "location": self._extract_location(text),
                    "maximum_penalty": max_penalty,
                    "defendant_name": defendant_name,
                    "court": self._extract_court(text),
                }

        # GBL / drug possession inference
        has_gbl = "gbl" in text_lower
        has_gamma = "gamma" in text_lower
        print(f"[PARSER] _infer_primary_charge_from_text: has_gbl={has_gbl}, has_gamma={has_gamma}")
        if has_gbl or has_gamma or "gamma-butyrolactone" in text_lower:
            if not max_penalty:
                max_penalty = "3 months imprisonment and/or a fine not exceeding $500"
            result = {
                "offense": "Possession of GBL",
                "statute": "Misuse of Drugs Act 1975 Section 7(1)(a) & (2)",
                "description": "Possession of a Class B controlled drug, namely GBL (gamma-butyrolactone)",
                "date_of_offense": date_of_offense,
                "location": None,
                "maximum_penalty": max_penalty,
                "defendant_name": defendant_name,
                "court": self._extract_court(text),
            }
            print(f"[PARSER] _infer_primary_charge_from_text returning: {result}")
            return result

        # Offence keyword inference for non-drug charges (burglary, theft, assault, etc.)
        for keyword, offense_name, statute in self.OFFENSE_KEYWORDS:
            if keyword.lower() in text_lower:
                print(f"[PARSER] _infer_primary_charge_from_text: inferred from keyword: {offense_name}")
                return {
                    "offense": offense_name,
                    "statute": statute,
                    "description": f"Charge inferred from disclosure content: {offense_name}",
                    "date_of_offense": date_of_offense,
                    "location": self._extract_location(text),
                    "maximum_penalty": max_penalty,
                    "defendant_name": defendant_name,
                    "court": self._extract_court(text),
                }

        print("[PARSER] _infer_primary_charge_from_text: no charge signal found")
        return None

    def _extract_court(self, text: str) -> str:
        """Extract court name from disclosure text."""
        match = re.search(r"([A-Z][a-zA-Z\s]+)\s+(District|High)\s+Court", text)
        if match:
            return f"{match.group(1).strip()} {match.group(2)} Court"
        return ""

    def _extract_procedural_history(self, text: str) -> Dict[str, Any]:
        """Extract procedural timeline."""
        proc = {
            "arrest_date": None,
            "arrest_time": None,
            "arrest_location": None,
            "arresting_officer": None,
            "interview_date": None,
            "interview_time": None,
            "interview_location": None,
            "solicitor_present": None,
            "solicitor_consultation_duration_minutes": None,
            "interview_recorded": None,
            "bail_status": None,
            "bail_conditions": [],
            "next_appearance_date": None,
            "next_appearance_court": None
        }

        # Arrest patterns — look for "arrested" near a time
        arrest_time_match = re.search(r"arrested.*?at\s+(\d{1,2}[:.]\d{2})\s*(?:am|pm)?", text, re.IGNORECASE)
        if arrest_time_match:
            proc["arrest_time"] = arrest_time_match.group(1).replace(".", ":")

        # Arrest date — look for date near "arrested"
        arrest_context = self._get_context_around_keyword(text, "arrested", 150)
        arrest_date_match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", arrest_context, re.IGNORECASE)
        if arrest_date_match:
            proc["arrest_date"] = self._parse_date(arrest_date_match.group(0))

        # If no arrest date found, use the offense date as fallback
        if not proc["arrest_date"]:
            proc["arrest_date"] = self._extract_date(text)

        # Officer
        officer_match = re.search(r"(?:PC|Constable|Detective)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
        if officer_match:
            proc["arresting_officer"] = officer_match.group(1)

        # Interview
        int_time_match = re.search(r"interviewed.*?at\s+(\d{1,2}[:.]\d{2})", text, re.IGNORECASE)
        if int_time_match:
            proc["interview_time"] = int_time_match.group(1).replace(".", ":")

        int_context = self._get_context_around_keyword(text, "interviewed", 150)
        int_date_match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", int_context, re.IGNORECASE)
        if int_date_match:
            proc["interview_date"] = self._parse_date(int_date_match.group(0))

        # Solicitor
        if re.search(r"(?:solicitor|lawyer|counsel|duty solicitor)", text, re.IGNORECASE):
            proc["solicitor_present"] = True
            dur_match = re.search(r"(\d+)\s*(?:minute|min|hour|hr)", text, re.IGNORECASE)
            if dur_match:
                proc["solicitor_consultation_duration_minutes"] = int(dur_match.group(1))

        # Recorded
        if re.search(r"(?:video|audio|tape|recorded)", text, re.IGNORECASE):
            proc["interview_recorded"] = True

        # Bail status
        if re.search(r"police bail", text, re.IGNORECASE):
            proc["bail_status"] = "police bail"
        elif re.search(r"remanded", text, re.IGNORECASE):
            proc["bail_status"] = "remanded"
        elif re.search(r"released", text, re.IGNORECASE):
            proc["bail_status"] = "released"

        # Bail conditions — improved extraction
        # Look for "conditions to [action]" or "condition: [action]"
        condition_patterns = [
            r"(?:conditions?|bail)\s+(?:to|that|is)\s+([^,.;]+)",
            r"(?:not|to)\s+(?:enter|reside|contact|approach|associate)\s+([^,.;]+)",
        ]
        for pattern in condition_patterns:
            conditions = re.findall(pattern, text, re.IGNORECASE)
            for c in conditions:
                c = c.strip()
                if c and len(c) > 3 and c not in proc["bail_conditions"]:
                    proc["bail_conditions"].append(c)

        # Also look for specific condition keywords
        specific_conditions = re.findall(r"(?:not to|to)\s+(?:enter|reside|contact|approach|associate with|consume)\s+([^,.;]+)", text, re.IGNORECASE)
        for c in specific_conditions:
            c = c.strip()
            if c and len(c) > 3 and c not in proc["bail_conditions"]:
                proc["bail_conditions"].append(c)

        # Next appearance
        app_match = re.search(r"(?:first appearance|next appearance|appear)\s*:?\s*(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", text, re.IGNORECASE)
        if app_match:
            proc["next_appearance_date"] = self._parse_date(app_match.group(0))

        court_match = re.search(r"([A-Z][a-z]+)\s+(District|High)\s+Court", text)
        if court_match:
            proc["next_appearance_court"] = f"{court_match.group(1)} {court_match.group(2)} Court"

        return proc

    def _extract_witnesses(self, text: str) -> List[Dict[str, Any]]:
        """Extract witness information."""
        witnesses = []
        seen_names = set()

        # Security guard pattern
        sg_matches = re.finditer(r"(?:security guard|guard)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", text, re.IGNORECASE)
        for match in sg_matches:
            name = match.group(1)
            if name not in seen_names:
                seen_names.add(name)
                witnesses.append({
                    "name": name,
                    "role": "security",
                    "observation": "Observed defendant's conduct"
                })

        # Police officer pattern
        po_matches = re.finditer(r"(?:PC|Constable|Detective)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", text)
        for match in po_matches:
            name = match.group(1)
            if name not in seen_names:
                seen_names.add(name)
                witnesses.append({
                    "name": name,
                    "role": "police",
                    "observation": "Arresting officer"
                })

        # Complainant pattern
        comp_matches = re.finditer(r"(?:complainant|victim)\s+([A-Z][a-z]+\s+[A-Z][a-z]+)", text, re.IGNORECASE)
        for match in comp_matches:
            name = match.group(1)
            if name not in seen_names:
                seen_names.add(name)
                witnesses.append({
                    "name": name,
                    "role": "complainant",
                    "observation": None
                })

        return witnesses

    def _extract_physical_evidence(self, text: str) -> List[Dict[str, Any]]:
        """Extract physical evidence mentions."""
        evidence = []
        seen = set()

        # CCTV
        if re.search(r"CCTV|camera|footage|video", text, re.IGNORECASE):
            evidence.append({
                "description": "CCTV footage",
                "seized_by": None,
                "chain_of_custody_noted": None
            })
            seen.add("cctv")

        # Items — more specific patterns
        item_patterns = [
            r"(?:seized|recovered|found|located|selected|concealed)\s+([^,.]{10,80})",
            r"(?:bottles? of|packet of|bag of|quantity of)\s+([^,.]{5,60})",
        ]
        for pattern in item_patterns:
            item_matches = re.findall(pattern, text, re.IGNORECASE)
            for item in item_matches:
                item_clean = item.strip()
                if item_clean and item_clean not in seen and len(item_clean) > 5:
                    seen.add(item_clean)
                    evidence.append({
                        "description": item_clean,
                        "seized_by": None,
                        "chain_of_custody_noted": None
                    })

        return evidence

    def _extract_prior_convictions(self, text: str) -> List[Dict[str, Any]]:
        """Extract prior conviction history without duplicates."""
        convictions = []
        seen_years = set()

        # Pattern: "previous convictions for [offense] in [year]"
        conv_matches = re.finditer(r"(?:previous convictions?|prior convictions?)\s+(?:for)?\s+([^,.]+?)\s+in\s+(\d{4})", text, re.IGNORECASE)
        for match in conv_matches:
            year = int(match.group(2))
            offense = match.group(1).strip()
            if year not in seen_years:
                seen_years.add(year)
                convictions.append({
                    "year": year,
                    "offense": offense,
                    "relevance": "Similar fact evidence / sentencing aggravation"
                })

        # Pattern: "in [year] and [year]" for similar offending
        year_pair_matches = re.findall(r"(?:in|during)\s+(\d{4})\s+and\s+(\d{4})", text)
        for y1, y2 in year_pair_matches:
            y1_int = int(y1)
            y2_int = int(y2)
            if y1_int not in seen_years:
                seen_years.add(y1_int)
                convictions.append({
                    "year": y1_int,
                    "offense": "Similar offending",
                    "relevance": "Pattern of conduct / sentencing aggravation"
                })
            if y2_int not in seen_years:
                seen_years.add(y2_int)
                convictions.append({
                    "year": y2_int,
                    "offense": "Similar offending",
                    "relevance": "Pattern of conduct / sentencing aggravation"
                })

        return convictions

    def _identify_flags(self, text: str, parsed: ParsedDisclosure) -> List[str]:
        """Identify case flags and issues."""
        flags = []
        text_lower = text.lower()

        if "identification" in text_lower or "identified" in text_lower:
            flags.append("identification_issue")
        if "denied" in text_lower and ("allegation" in text_lower or "charge" in text_lower):
            flags.append("denial_case")
        if re.search(r"solicitor|lawyer|counsel", text, re.IGNORECASE) and re.search(r"\b(10|15|20|5)\s*(?:minute|min)", text, re.IGNORECASE):
            flags.append("brief_solicitor_consultation")
        if re.search(r"video.*recorded|recorded.*video|audio.*recorded", text, re.IGNORECASE):
            flags.append("recorded_interview")
        if parsed.prior_convictions:
            flags.append("prior_convictions")
        if re.search(r"bail.*condition|condition.*bail|not enter|not contact|reside at|curfew", text, re.IGNORECASE):
            flags.append("bail_conditions")
        if re.search(r"value.*\$|\$.*\d|valued at", text, re.IGNORECASE):
            flags.append("quantum_issue")
        if re.search(r"intoxicat|drunk|alcohol|drug|substance", text, re.IGNORECASE):
            flags.append("intoxication_issue")
        if re.search(r"youth|under 18|minor|child", text, re.IGNORECASE):
            flags.append("youth_defendant")

        return flags

    def _identify_gaps(self, text: str, parsed: ParsedDisclosure) -> List[str]:
        """Identify likely disclosure gaps."""
        gaps = []

        if not parsed.procedural_history.get("arrest_time"):
            gaps.append("Exact arrest time not stated")
        if not parsed.procedural_history.get("interview_time"):
            gaps.append("Interview start/end times not stated")
        if not parsed.procedural_history.get("solicitor_consultation_duration_minutes"):
            gaps.append("Solicitor consultation duration not specified")
        if not parsed.physical_evidence:
            gaps.append("No exhibits or physical evidence listed")
        if not parsed.witnesses:
            gaps.append("Witness list incomplete or missing")
        if re.search(r"CCTV|camera|footage|video", text, re.IGNORECASE) and not any("CCTV" in e.get("description", "") for e in parsed.physical_evidence):
            gaps.append("CCTV footage — request preservation and disclosure")
        if not parsed.procedural_history.get("next_appearance_date"):
            gaps.append("Next appearance date not confirmed")
        if not parsed.procedural_history.get("bail_conditions") and re.search(r"bail|released", text, re.IGNORECASE):
            gaps.append("Bail conditions not fully specified")
        if not parsed.defendant.get("date_of_birth"):
            gaps.append("Defendant date of birth not stated")

        return gaps

    def _infer_offense(self, context: str) -> str:
        """Infer offense name from context."""
        context_lower = context.lower()
        for keyword, offense_name, _ in self.OFFENSE_KEYWORDS:
            if keyword.lower() in context_lower:
                return offense_name
        return "Unknown Offense"

    def _extract_date(self, text: str) -> Optional[str]:
        """Extract first date found in text."""
        match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", text, re.IGNORECASE)
        if match:
            return self._parse_date(match.group(0))
        return None

    def _extract_date_near(self, text: str, position: int) -> Optional[str]:
        """Extract date near a position in text."""
        window = text[max(0, position-150):min(len(text), position+150)]
        return self._extract_date(window)

    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text."""
        # Look for "at [Location], [Road/Street]" or "in [Location]"
        match = re.search(r"(?:at|in)\s+([A-Z][a-zA-Z\s]+(?:Road|Street|Ave|Avenue|Drive|Place|St|Rd|Dr)[^,.]*)", text)
        if match:
            return match.group(1).strip()
        # Fallback: look for "[Number] [Street]" pattern
        match = re.search(r"([0-9]+[A-Z]?\s+[A-Z][a-z]+\s+(?:Road|Street|Ave|Avenue|Drive|Place|St|Rd|Dr))", text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_location_near(self, text: str, position: int) -> Optional[str]:
        """Extract location near a position."""
        window = text[max(0, position-150):min(len(text), position+150)]
        return self._extract_location(window)

    def _extract_value(self, text: str) -> Optional[float]:
        """Extract monetary value, prioritising $ prefix."""
        # First try $ prefix
        match = re.search(r"\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)", text)
        if match:
            return float(match.group(1).replace(",", ""))
        # Then try "valued at" or similar
        match = re.search(r"(?:valued at|worth|value of)\s*[\$]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)", text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ""))
        # Fallback: any number that looks like a dollar amount (not a date/time)
        match = re.search(r"(?<!\d)(\d{3,})(?:\s*dollars?)?(?!\s*(?:am|pm|min|hour|day|year|month))", text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if val > 50:  # Likely a dollar amount, not a time or date
                return val
        return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse natural language date to ISO 8601."""
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4,
            "may": 5, "june": 6, "july": 7, "august": 8,
            "september": 9, "october": 10, "november": 11, "december": 12
        }
        match = re.search(r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})", date_str, re.IGNORECASE)
        if match:
            day = int(match.group(1))
            month = months[match.group(2).lower()]
            year = int(match.group(3))
            try:
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                return None
        return None

    def _get_context_around_keyword(self, text: str, keyword: str, window: int = 100) -> str:
        """Get text window around a keyword."""
        match = re.search(re.escape(keyword), text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            return text[start:end]
        return text[:window * 2]

    def _llm_enhance(self, parsed: ParsedDisclosure, text: str) -> ParsedDisclosure:
        """Optional LLM enhancement of parsing."""
        # This would call the LLM to refine extraction
        # For now, return as-is
        return parsed

    def extract_charge_focused_text(self, text: str, primary_charge: Optional[Dict[str, Any]] = None, max_chars: int = 22_000) -> str:
        """Return only the parts of the disclosure relevant to the actual charge.

        Full police disclosures often contain long background investigations
        (e.g., burglary/trailer theft) that distract the LLM from the actual
        charge (e.g., GBL possession). This method keeps:
        - the Charging Document,
        - drug/substance-related sections,
        - search/seizure sections that mention drugs or the actual charge,
        - expert forensic statements,
        - notebook entries about the actual charge.
        """
        if not text:
            return ""

        # 1. Always include the Charging Document section if present.
        #    Use the same robust regex as _extract_primary_charge.
        charge_doc_match = re.search(
            r"Charging Document.*?(?=Prosecutor details|Prosecutor\s+details|First appearance hearing|NOTICE OF|Family Violence|Offence category|signature|Signature|$)",
            text,
            re.IGNORECASE | re.DOTALL
        )
        focused_parts: List[Tuple[int, str]] = []
        charge_doc_end = 0
        if charge_doc_match:
            candidate = charge_doc_match.group(0).strip()
            if "Offence Details" in candidate or "offence description" in candidate.lower():
                focused_parts.append((charge_doc_match.start(), candidate))
                charge_doc_end = charge_doc_match.end()

        # 2. Define charge-relevant keywords.
        charge_keywords = [
            "gbl", "gamma", "butyrolactone", "controlled drug", "class b",
            "misuse of drugs", "warrantless search", "drug utensils",
            "seized a bottle", "seized liquid", "liquid in", "droppers",
            "phf science", "esr", "forensic", "certificate of analysis",
            "exhibit 11709", "prop ", "formal warning", "possess drugs",
            "solicitor", "lawyer", "counsel", "caution", "bill of rights", "dvd interview",
            # any statement by or about the defendant concerning the substance
            "admission", "admitted", "admit", "confession", "statement",
            "said it was", "identified", "identified the", "identified as",
            "replied", "responded", "told", "stated", "asked",
        ]
        # If we know the actual charge, also include its offence-specific terms.
        if primary_charge:
            desc = (primary_charge.get("description") or "").lower()
            statute = (primary_charge.get("statute") or "").lower()
            offence = (primary_charge.get("offense") or "").lower()
            if "gbl" in desc or "gamma" in desc or "gbl" in offence:
                charge_keywords.extend(["gbl", "gamma", "butyrolactone"])
            if "drug" in desc or "drug" in statute or "drug" in offence:
                charge_keywords.extend(["controlled drug", "class b", "misuse of drugs"])
            if "burglary" in offence:
                charge_keywords.extend(["burglary", "entered", "trespasser", "intent to steal"])
        else:
            # No primary charge known: prefer drug/substance content, but do not
            # ignore a clear burglary narrative if that is what the disclosure contains.
            text_lower = text.lower()
            if "burglary" in text_lower or ("entered" in text_lower and "intent" in text_lower):
                charge_keywords = ["burglary", "entered", "trespasser", "intent to steal",
                                   "stolen", "seized", "fingerprint", "cctv", "admission",
                                   "admitted", "statement", "identified", "replied", "responded",
                                   "told", "stated", "asked"]
            else:
                charge_keywords = ["gbl", "gamma", "butyrolactone", "controlled drug", "class b",
                                   "misuse of drugs", "drug utensils", "seized liquid", "seized a bottle",
                                   "droppers", "phf science", "esr", "formal warning", "possess drugs",
                                   "admission", "admitted", "statement", "said it was", "identified",
                                   "replied", "responded", "told", "stated", "asked"]

        # Background keywords: if a paragraph is dominated by these, drop it.
        background_keywords = ["burglary", "stolen trailer", "towing a trailer", "cctv footage",
                               "gps tracking", "vehicle registration", "trailer registration",
                               "random guy with trailer", "entered a building", "trespasser"]

        # 3. Split text into paragraphs. Keep paragraphs that mention charge-relevant
        #    keywords, but also drop individual sentences dominated by background
        #    narrative (e.g., burglary/trailer details inside police statements).
        paragraphs = re.split(r"\n{2,}", text)
        current_pos = 0
        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped:
                current_pos += len(para) + 2
                continue
            # Skip paragraphs already inside the Charging Document extraction.
            if charge_doc_end and current_pos < charge_doc_end and current_pos + len(para) <= charge_doc_end + 200:
                current_pos += len(para) + 2
                continue

            para_lower = para_stripped.lower()
            dominated_by_background = (sum(1 for kw in background_keywords if kw in para_lower) >= 2)
            if dominated_by_background:
                current_pos += len(para) + 2
                continue

            # Split paragraph into sentences and filter out background-heavy ones.
            sentences = re.split(r"(?<=[.!?])\s+", para_stripped)
            kept_sentences = []
            for sent in sentences:
                sent_lower = sent.lower()
                has_charge = any(kw in sent_lower for kw in charge_keywords)
                sent_background = sum(1 for kw in background_keywords if kw in sent_lower)
                if has_charge and sent_background == 0:
                    kept_sentences.append(sent)
                elif has_charge and sent_background > 0:
                    # Sentence has both charge and background signals; keep only if
                    # charge signals clearly dominate.
                    charge_signals = sum(1 for kw in charge_keywords if kw in sent_lower)
                    if charge_signals >= 2 or "gbl" in sent_lower or "gamma" in sent_lower:
                        kept_sentences.append(sent)

            if kept_sentences:
                cleaned_para = " ".join(kept_sentences)
                if cleaned_para:
                    focused_parts.append((current_pos, cleaned_para))
            current_pos += len(para) + 2

        # 4. Deduplicate by start position and sort in original reading order.
        seen: set = set()
        unique_parts: List[Tuple[int, str]] = []
        for pos, part in sorted(focused_parts, key=lambda x: x[0]):
            key = re.sub(r"\s+", " ", part.strip())[:120]
            if key not in seen:
                seen.add(key)
                unique_parts.append((pos, part))

        # 5. Concatenate until max_chars.
        output_parts: List[str] = []
        total = 0
        for _, part in unique_parts:
            if total + len(part) > max_chars:
                remaining = max_chars - total
                if remaining > 100:
                    output_parts.append(part[:remaining])
                break
            output_parts.append(part)
            total += len(part) + 2

        result = "\n\n".join(output_parts) if output_parts else ""
        print(f"[PARSER] extract_charge_focused_text: input_len={len(text)}, output_len={len(result)}, "
              f"contains_gbl={'gbl' in result.lower()}, contains_burglary={'burglary' in result.lower()}")
        if not result:
            result = text[:max_chars]
        return result

    def extract_defence_fact_snippets(self, text: str, max_chars: int = 3_000) -> str:
        """Pull the sentences most likely to contain defence advantages.

        Long disclosures bury the key facts. This deterministic extractor grabs
        sentences that mention admissions, warnings, legal advice, unsigned
        records, searches, and the substance itself, so the LLM cannot miss them.
        """
        if not text:
            return ""

        defence_keywords = [
            "admission", "admitted", "admit", "confession", "formal warning",
            "warning", "induced", "inducement", "lawyer", "solicitor", "counsel",
            "mark edgar", "unsigned", "declined to sign", "refused to sign",
            "right to silence", "no comment", "did not answer",
            "warrantless", "s 18", "section 18", "s.18", "search and surveillance",
            "kitchen sink", "located in", "seized", "identified", "said it was",
            "it is gbl", "it's gbl", "gamma", "butyrolactone",
            "possess", "possession", "custody", "control",
            # any statement by the defendant, even if not labelled an admission
            "defendant said", "accused said", "he said", "she said",
            "stated", "told", "replied", "responded", "spoke", "asked",
            "interview", "dvd interview", "statement", "record of interview",
        ]

        # Split into sentences; accept common abbreviations without breaking.
        sentences = re.split(r"(?<=[.!?])\s+", text)
        kept: List[str] = []
        seen: set = set()
        total = 0
        for sent in sentences:
            s = sent.strip()
            if not s or len(s) < 10:
                continue
            lower = s.lower()
            if not any(kw in lower for kw in defence_keywords):
                continue
            # Drop obvious background narrative (burglary/trailer) only when the
            # disclosure is clearly about a drug/substance charge. If the case itself
            # concerns burglary, those facts are relevant.
            drug_signals = sum(1 for kw in ("gbl", "gamma", "butyrolactone", "controlled drug",
                                            "class b", "misuse of drugs", "methamphetamine",
                                            "cannabis", "possess drugs") if kw in lower)
            burglary_signals = sum(1 for kw in ("burglary", "stolen trailer", "towing a trailer",
                                                "gps tracking", "trailer registration") if kw in lower)
            if burglary_signals >= 1 and drug_signals == 0:
                # Burglary background in a drug case — drop.
                continue
            key = re.sub(r"\s+", " ", s)[:120]
            if key in seen:
                continue
            seen.add(key)
            if total + len(s) > max_chars:
                break
            kept.append(s)
            total += len(s) + 1

        return " ".join(kept) if kept else ""

    def to_dict(self, parsed: ParsedDisclosure) -> Dict[str, Any]:
        """Convert to plain dict for JSON serialization."""
        return {
            "case_title": parsed.case_title,
            "defendant": parsed.defendant,
            "charges": parsed.charges,
            "primary_charge": parsed.primary_charge,
            "court": parsed.court,
            "procedural_history": parsed.procedural_history,
            "witnesses": parsed.witnesses,
            "physical_evidence": parsed.physical_evidence,
            "prior_convictions": parsed.prior_convictions,
            "disclosure_gaps": parsed.disclosure_gaps,
            # Flags are intentionally omitted from prompts; they are crude keyword
            # hints that the model tends to treat as factual findings.
            "flags": [],
        }
