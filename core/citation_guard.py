#!/usr/bin/env python3
"""
Citation Guard for NZ Legal RAG

Verifies that LLM-generated citations actually exist in the retrieved
source documents. Flags hallucinated case names, section numbers, and
statute references before they reach the user.
"""

import re
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass


@dataclass
class CitationCheck:
    citation: str
    verified: bool
    source_matches: List[str]


class CitationGuard:
    """
    Post-processing guard that cross-checks LLM citations against
    the retrieved chunks provided in the prompt context.
    """

    # Patterns for NZ legal citations
    CASE_PATTERNS = [
        re.compile(r'R\s+v\s+[A-Z][a-zA-Z\s]+\[[0-9]{4}\][^.,;\n]+', re.IGNORECASE),
        re.compile(r'\[[0-9]{4}\]\s+\d+\s+NZLR\s+\d+', re.IGNORECASE),
        re.compile(r'\[[0-9]{4}\]\s+NZSC\s+\d+', re.IGNORECASE),
        re.compile(r'\[[0-9]{4}\]\s+NZCA\s+\d+', re.IGNORECASE),
        re.compile(r'\[[0-9]{4}\]\s+NZHC\s+\d+', re.IGNORECASE),
        re.compile(r'\[[0-9]{4}\]\s+NZDC\s+\d+', re.IGNORECASE),
        re.compile(r'\([0-9]{4}\)\s+\d+\s+CRNZ\s+\d+', re.IGNORECASE),
    ]

    LEGISLATION_PATTERNS = [
        re.compile(
            r'(Crimes Act|Misuse of Drugs Act|Evidence Act|Search and Surveillance Act|'
            r'Criminal Procedure Act|Bill of Rights Act|Privacy Act|Corrections Act|'
            r'Immigration Act|Domestic Violence Act|Harassment Act|Sale and Supply of Alcohol Act|'
            r'Criminal Proceeds \(Recovery\) Act)\s+[0-9]{4}',
            re.IGNORECASE
        ),
        re.compile(
            r's(?:ection)?\s*\d+[A-Z]?\s+(?:of\s+)?(?:the\s+)?'
            r'(Crimes|Misuse of Drugs|Evidence|Search and Surveillance|Criminal Procedure|'
            r'Bill of Rights|Privacy|Corrections|Immigration|Domestic Violence|Harassment)',
            re.IGNORECASE
        ),
    ]

    SECTION_PATTERNS = [
        re.compile(r's(?:ection)?\s*\d+[A-Z]?\s*\(?[0-9]+\)?', re.IGNORECASE),
        re.compile(r'ss\s*\d+[A-Z]?\s*-\s*\d+[A-Z]?', re.IGNORECASE),
    ]

    def __init__(self):
        self.source_cache: Dict[str, Set[str]] = {}

    def _normalize(self, text: str) -> str:
        """Lower-case, strip punctuation, collapse spaces."""
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _extract_fragments(self, text: str) -> Set[str]:
        """
        Extract searchable fragments from source text.
        We index n-grams and individual citation-like tokens so that
        partial matches still work.
        """
        fragments = set()
        normalized = self._normalize(text)

        # Full text
        fragments.add(normalized)

        # Word n-grams (3-6 words) to catch phrase matches
        words = normalized.split()
        for n in range(3, min(7, len(words) + 1)):
            for i in range(len(words) - n + 1):
                fragments.add(' '.join(words[i:i + n]))

        # Specific citation-like tokens
        for pattern in self.CASE_PATTERNS + self.LEGISLATION_PATTERNS:
            for match in pattern.finditer(text):
                fragments.add(self._normalize(match.group(0)))

        return fragments

    def index_sources(self, sources: List[str]) -> None:
        """Build searchable index from retrieved source chunks."""
        self.source_cache = {}
        all_fragments: Set[str] = set()
        for i, src in enumerate(sources):
            frags = self._extract_fragments(src)
            self.source_cache[str(i)] = frags
            all_fragments.update(frags)
        self.source_cache['__all__'] = all_fragments

    def extract_citations(self, text: str) -> List[str]:
        """Pull every citation-like string from the LLM response."""
        found = []
        for pattern in self.CASE_PATTERNS + self.LEGISLATION_PATTERNS:
            for match in pattern.finditer(text):
                citation = match.group(0).strip()
                if citation and citation not in found:
                    found.append(citation)
        return found

    def verify(self, response: str, sources: List[str]) -> Tuple[List[CitationCheck], float, str]:
        """
        Verify citations in *response* against *sources*.

        Returns:
            - List of CitationCheck objects
            - Verification score (0.0 – 1.0)
            - A short warning message (empty if all good)
        """
        self.index_sources(sources)
        citations = self.extract_citations(response)

        if not citations:
            # No citations made — neutral score, mild warning for legal analysis
            return [], 0.5, ""

        checks = []
        verified_count = 0

        for citation in citations:
            norm_cite = self._normalize(citation)
            matched = False
            matches = []

            # Exact or near-exact match in any source fragment
            for idx, frags in self.source_cache.items():
                if idx == '__all__':
                    continue
                if norm_cite in frags:
                    matched = True
                    matches.append(f"source_{idx}")
                else:
                    # Fuzzy: check if most words appear together in a fragment
                    cite_words = set(norm_cite.split())
                    for frag in frags:
                        frag_words = set(frag.split())
                        # If >70% of citation words appear in a single fragment
                        if cite_words and len(cite_words & frag_words) / len(cite_words) >= 0.7:
                            matched = True
                            matches.append(f"source_{idx}")
                            break

            if matched:
                verified_count += 1

            checks.append(CitationCheck(
                citation=citation,
                verified=matched,
                source_matches=list(set(matches))
            ))

        score = verified_count / len(citations) if citations else 0.5

        # Build warning
        unverified = [c.citation for c in checks if not c.verified]
        warning = ""
        if unverified:
            warning = (
                f"\n\n⚠️  CITATION WARNING: The following {len(unverified)} citation(s) "
                f"could not be verified against the retrieved source documents and may be "
                f"hallucinated: {', '.join(unverified)}. "
                f"Please verify independently before relying on them in court."
            )

        return checks, score, warning

    def strip_hallucinated_citations(self, response: str, sources: List[str]) -> str:
        """
        Aggressive mode: remove sentences that contain unverified citations.
        Use sparingly — better to warn the user and let them decide.
        """
        checks, _, _ = self.verify(response, sources)
        bad_citations = {c.citation for c in checks if not c.verified}

        if not bad_citations:
            return response

        sentences = re.split(r'(?<=[.!?])\s+', response)
        cleaned = []
        for sentence in sentences:
            if not any(bc in sentence for bc in bad_citations):
                cleaned.append(sentence)
            else:
                # Replace with a placeholder rather than silent deletion
                cleaned.append(
                    "[Sentence containing unverified citation removed — "
                    "see warning above.]"
                )

        return ' '.join(cleaned)
