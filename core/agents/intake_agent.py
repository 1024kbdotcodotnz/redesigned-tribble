#!/usr/bin/env python3
"""
Case Intake Agent

Parses raw user input, determines analysis type, extracts key legal entities,
generates optimised search queries, and routes to the correct collection set.
"""

import json
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class IntakeResult:
    """Structured output from the Case Intake Agent."""
    detected_analysis_type: str = "general"
    refined_query: str = ""
    key_entities: Dict[str, List[str]] = field(default_factory=dict)
    suggested_collections: List[str] = field(default_factory=list)
    intake_summary: str = ""
    search_queries: List[str] = field(default_factory=list)
    confidence: float = 1.0  # How certain the agent is about its classification


class CaseIntakeAgent:
    """
    First agent in the pipeline.

    Responsibilities:
    1. Classify the user's intent into an analysis type.
    2. Extract names, charges, statutes, and case references.
    3. Rewrite the raw query into search-optimised queries.
    4. Recommend which vector DB collections to search.
    5. Produce a brief intake summary for the audit trail.
    """

    ANALYSIS_TYPES = ["general", "charge_review", "search_warrant", "evidence_review", "disclosure_review"]

    KNOWN_COLLECTIONS = {
        "nz_legislation": "NZ Acts and Regulations",
        "nz_case_law": "NZ Case Law",
        "nzlii_criminal_cases": "NZLII Criminal Cases",
        "nz_police_manual": "NZ Police Manual",
        "legal_research": "General Legal Research",
        "user_uploads": "User Uploaded Documents",
        "confidential": "Confidential Documents",
    }

    def __init__(self, llm: Any):
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def intake(self, raw_query: str, available_collections: Optional[List[str]] = None,
               file_context: Optional[str] = None) -> IntakeResult:
        """Run the intake pipeline on a raw user query."""

        if available_collections is None:
            available_collections = list(self.KNOWN_COLLECTIONS.keys())

        prompt = self._build_intake_prompt(raw_query, available_collections, file_context)

        try:
            response = self.llm.invoke(prompt)
        except Exception as e:
            # Graceful degradation — fall back to raw query
            return self._fallback_result(raw_query, available_collections, f"LLM error: {e}")

        parsed = self._parse_json_response(response)

        if not parsed:
            return self._fallback_result(raw_query, available_collections, "JSON parse failed")

        return self._hydrate_result(parsed, raw_query, available_collections)

    # ------------------------------------------------------------------
    # Prompt engineering
    # ------------------------------------------------------------------

    def _build_intake_prompt(self, raw_query: str, collections: List[str],
                             file_context: Optional[str]) -> str:
        coll_descriptions = "\n".join(
            f"  - {c}: {self.KNOWN_COLLECTIONS.get(c, 'Unknown')}"
            for c in collections if not c.startswith("temp_session_")
        )

        file_hint = ""
        if file_context:
            file_hint = f"\nThe user has also uploaded the following document(s): {file_context}\n"

        return f"""You are the Case Intake Agent for a New Zealand criminal defence legal research system.
Your job is to read the raw user query and produce a structured JSON object that downstream agents will use.

RULES:
1. Detect the analysis_type from: general, charge_review, search_warrant, evidence_review, disclosure_review.
2. refined_query should be a clean, legally-focused version of the user's question.
3. search_queries should be 2–3 distinct search queries optimised for semantic retrieval in a vector database.
4. suggested_collections should list which of the available collections are most relevant.
5. key_entities should extract case names (e.g. "R v Smith"), charges, statutes, and any people mentioned.
6. intake_summary should be one sentence summarising what the user wants.
7. confidence should be 0.0–1.0 representing how clear the user's intent is.
8. Respond ONLY with valid JSON. No markdown code fences, no explanation, no <think> tags.

AVAILABLE COLLECTIONS:
{coll_descriptions}
{file_hint}
RAW USER QUERY:
{raw_query}

RESPOND WITH EXACTLY THIS JSON SCHEMA:
{{
  "detected_analysis_type": "...",
  "refined_query": "...",
  "search_queries": ["...", "..."],
  "suggested_collections": ["..."],
  "key_entities": {{
    "case_names": [],
    "charges": [],
    "statutes": [],
    "people": []
  }},
  "intake_summary": "...",
  "confidence": 0.95
}}
"""

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_response(text: str) -> Optional[Dict]:
        """Extract and parse JSON from an LLM response."""
        if not text:
            return None

        # Strip DeepSeek / reasoning tags
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        # Try to find JSON inside markdown code fences
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1)
        else:
            # Find the first JSON object
            brace_match = re.search(r"\{.*\}", text, re.DOTALL)
            if brace_match:
                text = brace_match.group(0)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    def _hydrate_result(self, parsed: Dict, raw_query: str,
                        available: List[str]) -> IntakeResult:
        """Convert parsed JSON into a typed IntakeResult."""

        analysis_type = str(parsed.get("detected_analysis_type") or "general").lower().strip()
``````if analysis_type not in self.ANALYSIS_TYPES:
    ``analysis_type = "general"

        suggested = parsed.get("suggested_collections", [])
        # Filter to only collections that actually exist
        suggested = [c for c in suggested if c in available]
        # Always include temp_session collections if present in available
        temp_colls = [c for c in available if c.startswith("temp_session_")]
        for tc in temp_colls:
            if tc not in suggested:
                suggested.insert(0, tc)

        # Ensure at least some permanent collections if nothing suggested
        if not suggested or all(c.startswith("temp_session_") for c in suggested):
            defaults = ["nz_legislation", "nz_case_law", "nz_police_manual"]
            for d in defaults:
                if d in available and d not in suggested:
                    suggested.append(d)

        key_entities = parsed.get("key_entities", {})
        if not isinstance(key_entities, dict):
            key_entities = {}

        search_queries = parsed.get("search_queries", [])
        if not isinstance(search_queries, list) or not search_queries:
            search_queries = [raw_query]

        # Ensure refined_query exists
        refined = str(parsed.get("refined_query") or "").strip()
        if not refined:
            refined = raw_query

        return IntakeResult(
            detected_analysis_type=analysis_type,
            refined_query=refined,
            key_entities=key_entities,
            suggested_collections=suggested,
            intake_summary=parsed.get("intake_summary", ""),
            search_queries=search_queries,
            confidence=float(parsed.get("confidence", 0.8))
        )

    def _fallback_result(self, raw_query: str, available: List[str],
                         reason: str) -> IntakeResult:
        """Graceful fallback when the LLM fails or returns unparsable output."""
        temp_colls = [c for c in available if c.startswith("temp_session_")]
        defaults = [c for c in ["nz_legislation", "nz_case_law", "nz_police_manual"] if c in available]
        return IntakeResult(
            detected_analysis_type="general",
            refined_query=raw_query,
            key_entities={},
            suggested_collections=temp_colls + defaults,
            intake_summary=f"[Fallback] {reason}",
            search_queries=[raw_query],
            confidence=0.5
        )
