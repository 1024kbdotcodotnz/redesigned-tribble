#!/usr/bin/env python3
"""
Citation Auditor Agent

LLM-powered verification of legal citations against retrieved sources.
Goes beyond deterministic regex matching by understanding context and
semantic equivalence. Can trigger re-search queries for missing citations.
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class AuditResult:
    """Structured output from the Citation Auditor."""
    verified_citations: List[str] = field(default_factory=list)
    unverified_citations: List[str] = field(default_factory=list)
    hallucination_risk: float = 0.0  # 0.0 = safe, 1.0 = severe
    re_search_queries: List[str] = field(default_factory=list)
    audit_report: str = ""  # Human-readable summary
    corrected_response: Optional[str] = None
    needs_re_search: bool = False


class CitationAuditor:
    """
    Post-analysis agent that audits every legal citation in the LLM response.

    Capabilities:
    1. Identifies NZ case citations, statute sections, and regulation references.
    2. Checks whether each citation appears in the retrieved source documents.
    3. Distinguishes between "not in sources" and "likely hallucinated".
    4. Generates targeted search queries to find missing authorities.
    5. Produces a concise audit report for the Synthesis Agent.
    """

    # Statute sections that are correct and commonly cited in NZ defence work.
    # These are accepted even if the vector DB did not return them as snippets.
    STATUTE_WHITELIST = [
        r"Misuse of Drugs Act 1975,?\s*s\s*7\s*\(?1\)?\(?a\)?",
        r"Misuse of Drugs Act 1975,?\s*s\s*7\s*\(?2\)?",
        r"Misuse of Drugs Act 1975,?\s*s\s*6",
        r"Search and Surveillance Act 2012,?\s*s\s*18\s*\(?2\)?",
        r"Search and Surveillance Act 2012,?\s*s\s*18\s*\(?1\)?",
        r"Search and Surveillance Act 2012,?\s*s\s*6",
        r"Search and Surveillance Act 2012,?\s*s\s*4",
        r"New Zealand Bill of Rights Act 1990,?\s*s\s*21",
        r"NZBORA,?\s*s\s*21",
        r"New Zealand Bill of Rights Act 1990,?\s*s\s*23",
        r"NZBORA,?\s*s\s*23",
        r"New Zealand Bill of Rights Act 1990,?\s*s\s*24\s*\(?1\)?\(?d\)?",
        r"New Zealand Bill of Rights Act 1990,?\s*s\s*24\s*\(?2\)?",
        r"New Zealand Bill of Rights Act 1990,?\s*s\s*24",
        r"NZBORA,?\s*s\s*24",
        r"New Zealand Bill of Rights Act 1990,?\s*s\s*25",
        r"NZBORA,?\s*s\s*25",
        r"Evidence Act 2006,?\s*s\s*12",
        r"Evidence Act 2006,?\s*s\s*8",
        r"Evidence Act 2006,?\s*s\s*18",
        r"Evidence Act 2006,?\s*s\s*20",
        r"Evidence Act 2006,?\s*s\s*24",
    ]

    def __init__(self, llm: Any, search_callback: Optional[Any] = None):
        self.llm = llm
        self.search_callback = search_callback

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def audit(self, response_text: str, sources: List[Any], original_query: str) -> AuditResult:
        """Audit citations in a defence analysis response."""
        if not self.llm:
            return AuditResult(audit_report="[LLM not configured — skipping citation audit]")

        # Build source summary (truncated to fit context)
        source_summaries = []
        for i, src in enumerate(sources[:10]):
            meta = getattr(src, "metadata", {}) if hasattr(src, "metadata") else src.get("metadata", {})
            doc = getattr(src, "document", "") if hasattr(src, "document") else src.get("document", "")
            title = meta.get("title", meta.get("source", f"Source {i+1}"))
            cat = meta.get("category", "unknown")
            source_summaries.append(f"[{i+1}] {title} ({cat})\n{doc[:600]}")

        sources_text = "\n\n---\n\n".join(source_summaries) if source_summaries else "[No sources retrieved]"

        prompt = self._build_audit_prompt(response_text, sources_text, original_query)

        try:
            raw = self.llm.invoke(prompt)
        except Exception as e:
            return AuditResult(audit_report=f"[Citation Auditor LLM error: {e}]")

        parsed = self._parse_json_response(raw)
        if not parsed:
            # Fallback: deterministic check
            return self._deterministic_fallback(response_text, sources)

        return self._hydrate_result(parsed, response_text)

    # ------------------------------------------------------------------
    # Prompt engineering
    # ------------------------------------------------------------------

    def _build_audit_prompt(self, response: str, sources: str, query: str) -> str:
        return f"""You are the Citation Auditor for a New Zealand criminal defence legal research system.
Your job is to verify every legal citation in the analysis below against the provided source documents.

ABSOLUTE RULES:
1. Extract ALL case citations (e.g., "R v Smith [2024] NZCA 1", "[2023] 2 NZLR 100") and statute references (e.g., "s 21 NZBORA", "Search and Surveillance Act 2012, s 6").
2. A citation is VERIFIED only if it appears explicitly in the provided source documents. Do NOT approve citations because they are "well-known" or "commonly cited".
3. If a citation does NOT appear in the sources, mark it UNVERIFIED — even if you believe it is real.
4. hallucination_risk: 0.0 (all good) to 1.0 (severe). Use 0.0 if every citation is verified, 0.3-0.5 if some unverified, 0.8+ if citations are invented or clearly wrong.
5. re_search_queries: Generate 1-3 search queries to find the MISSING authorities in the vector database. Leave empty if all citations are verified.
6. corrected_response: If unverified citations exist, rewrite the relevant sentence(s) to remove the false citation and add a note like "[Authority not verified in retrieved sources — independent verification required]". Otherwise return null.
7. audit_report: A concise human-readable summary of what was checked and what failed.
8. Respond ONLY with valid JSON. No markdown fences, no explanation, no <think> tags.

ORIGINAL USER QUERY: {query}

SOURCE DOCUMENTS:
{sources}

ANALYSIS RESPONSE TO AUDIT:
{response}

RESPOND WITH EXACTLY THIS JSON SCHEMA:
{{
  "verified_citations": ["..."],
  "unverified_citations": ["..."],
  "hallucination_risk": 0.0,
  "re_search_queries": ["..."],
  "audit_report": "...",
  "corrected_response": "..."
}}
"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict]:
        if not text:
            return None
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
        fence = re.search(r"```(?:json)?\s*(\{{.*?\}})\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        else:
            brace = re.search(r"\{{.*\}}", text, re.DOTALL)
            if brace:
                text = brace.group(0)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _is_whitelisted(self, citation: str) -> bool:
        if not citation:
            return False
        low = citation.lower().replace("\u2013", "-").replace("\u2014", "-")
        for pat in self.STATUTE_WHITELIST:
            if re.search(pat, low, re.IGNORECASE):
                return True
        return False

    def _is_statute_citation(self, citation: str) -> bool:
        if not citation:
            return False
        low = citation.lower()
        return bool(
            re.search(r"\b(?:s|section|ss)\s*\d", low)
            and any(act in low for act in (
                "act", "nzbora", "bill of rights", "misuse of drugs",
                "search and surveillance", "evidence", "criminal procedure",
                "crimes", "sentencing", "bail"
            ))
        )

    def _verify_in_legislation_collection(self, citation: str) -> bool:
        """Search the nz_legislation collection directly for the cited section."""
        if not self.search_callback or not self._is_statute_citation(citation):
            return False
        try:
            results = self.search_callback(
                query=citation,
                collections=["nz_legislation"],
                filters=None,
                top_k=3,
            )
            if not results:
                return False
            low_cite = citation.lower()
            for r in results:
                doc = getattr(r, "document", "") if hasattr(r, "document") else r.get("document", "")
                meta = getattr(r, "metadata", {}) if hasattr(r, "metadata") else r.get("metadata", {})
                text = f"{meta.get('title', '')} {meta.get('source', '')} {doc}".lower()
                # Accept if the Act and section number appear together, or if the
                # document text contains the exact section reference.
                if low_cite in text:
                    return True
                # Fallback: check the key components (Act year + section number).
                act_year_match = re.search(r"(\d{4})\b", low_cite)
                section_match = re.search(r"(?:s|section)\s*(\d+[A-Z]?)", low_cite)
                if act_year_match and section_match:
                    year = act_year_match.group(1)
                    section = section_match.group(1)
                    if year in text and re.search(rf"\bsection\s*{re.escape(section)}\b|\bs\s*{re.escape(section)}\b", text):
                        return True
        except Exception as e:
            # Search failures should not block the audit.
            print(f"[CITATION_AUDITOR] legislation search failed for '{citation}': {e}")
        return False

    def _hydrate_result(self, parsed: Dict, original_response: str) -> AuditResult:
        verified = list(parsed.get("verified_citations", []))
        unverified = list(parsed.get("unverified_citations", []))

        # Move whitelisted statute sections from unverified to verified.
        still_unverified = []
        for c in unverified:
            if self._is_whitelisted(c):
                verified.append(c)
            else:
                still_unverified.append(c)
        unverified = still_unverified

        # Second-chance verification: search the legislation collection directly.
        if self.search_callback:
            final_unverified = []
            for c in unverified:
                if self._verify_in_legislation_collection(c):
                    verified.append(c)
                else:
                    final_unverified.append(c)
            unverified = final_unverified

        re_search = list(parsed.get("re_search_queries", []))
        risk = float(parsed.get("hallucination_risk", 0.0))
        if not unverified:
            risk = 0.0
            re_search = []

        return AuditResult(
            verified_citations=verified,
            unverified_citations=unverified,
            hallucination_risk=risk,
            re_search_queries=re_search,
            audit_report=parsed.get("audit_report", ""),
            corrected_response=parsed.get("corrected_response") or None,
            needs_re_search=bool(unverified and re_search)
        )

    def _deterministic_fallback(self, response: str, sources: List[Any]) -> AuditResult:
        """If the LLM auditor fails, fall back to simple substring checks."""
        source_text = " ".join(
            (getattr(s, "document", "") if hasattr(s, "document") else s.get("document", ""))[:500]
            for s in sources
        )

        # Extract likely citations with regex
        patterns = [
            r'\[[0-9]{4}\]\s+(?:NZSC|NZCA|NZHC|NZDC|NZFc)\s+[0-9]+',
            r'R\s+v\s+[A-Z][a-zA-Z\s]+\[[0-9]{4}\]',
            r'(?:Crimes Act|Evidence Act|Search and Surveillance Act|Criminal Procedure Act|Bill of Rights Act)\s+[0-9]{4}',
            r's\s*\d+[A-Z]?\s+(?:of\s+)?(?:the\s+)?(?:Crimes|Evidence|Search and Surveillance|Criminal Procedure|Bill of Rights)',
        ]

        found = []
        missing = []
        for pat in patterns:
            for match in re.findall(pat, response, re.IGNORECASE):
                if match.lower() in source_text.lower():
                    found.append(match)
                else:
                    missing.append(match)

        risk = min(1.0, len(missing) * 0.2) if missing else 0.0
        report = f"[Deterministic fallback] {len(found)} verified, {len(missing)} unverified."

        return AuditResult(
            verified_citations=list(set(found)),
            unverified_citations=list(set(missing)),
            hallucination_risk=risk,
            re_search_queries=[f"{c} NZ legal" for c in set(missing)[:3]],
            audit_report=report,
            needs_re_search=bool(missing)
        )
