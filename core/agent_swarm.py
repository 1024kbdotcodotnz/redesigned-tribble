#!/usr/bin/env python3
"""
NZ Legal RAG — Agent Swarm System (Production v2)
6-agent multi-KC pipeline with real LLM calls, RAG integration, and parallel execution.
"""

import os
import re
import json
import time
import concurrent.futures
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional

from core.prompts import PROMPTS
from core.parser import DisclosureParser, ParsedDisclosure
from core.fact_sheet_builder import FactSheetBuilder


def ollama_unload_model(model: str, host: str = "http://localhost:11434") -> None:
    """Ask Ollama to unload a model from GPU memory immediately."""
    import requests
    try:
        requests.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
            timeout=30,
        )
        print(f"[OLLAMA] unload request sent for {model}")
    except Exception as e:
        print(f"[OLLAMA] unload request failed: {e}")


@dataclass
class ExpertAnalysis:
    expert_name: str = ""
    key_findings: List[str] = field(default_factory=list)
    raw_output: str = ""


@dataclass
class SynthesizedReport:
    # New legal-brief structure matching the target output format
    title_block: str = ""
    table_of_contents: str = ""
    executive_summary: str = ""
    charge_and_legislative_framework: str = ""
    summary_of_evidence: str = ""
    assessment_of_prosecution_case: str = ""
    evidence_analysis: str = ""
    elements_of_the_offence: str = ""
    defence_strategies: str = ""
    cross_examination_priorities: str = ""
    disclosure_and_forensic_gaps: str = ""
    instructions_to_counsel_pre_trial: str = ""
    pre_trial_instructions_for_lawyer: str = ""
    evidentiary_issues_to_raise: str = ""
    conclusion: str = ""
    conclusion_and_risk_assessment: str = ""
    disclaimer: str = ""
    # Legacy fields kept for backward compatibility
    disclosure_overview: str = ""
    charge_analysis: str = ""
    summary_of_facts_review: str = ""
    police_conduct_assessment: str = ""
    further_disclosure_required: str = ""
    bail_analysis: str = ""
    options_and_recommendations: str = ""
    expert_consensus_and_divergence: str = ""
    risk_assessment: str = ""


class OllamaLLMClient:
    """Client for Ollama LLM API."""
    
    FORMAT_ENFORCEMENT = """
IMPORTANT: You must respond ONLY with the structured analysis requested above.
Do not include any unrelated text, mathematical problems, code, or random content.
Do not deviate from the requested format. Stay focused on New Zealand criminal law.
"""
    
    def __init__(self, model: str = "qwen2.5:14b", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
    
    def generate(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 4000) -> str:
        import requests
        try:
            enforced_prompt = prompt + self.FORMAT_ENFORCEMENT
            full_prompt = f"{system}\n\n{enforced_prompt}" if system else enforced_prompt
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {
                        "temperature": temperature,
                        "num_ctx": 16384,
                        "num_predict": max_tokens,
                        "num_gpu": 999,
                    }
                },
                timeout=int(os.getenv("OLLAMA_REQUEST_TIMEOUT", "1800"))
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            print(f"Ollama error: {e}")
            return f"[Error: {e}]"
    
    def generate_json(self, prompt: str, system: str = "", temperature: float = 0.1, max_tokens: int = 4000) -> Dict[str, Any]:
        """Generate and parse JSON response."""
        raw = self.generate(prompt, system, temperature, max_tokens)
        try:
            json_match = raw.strip()
            if "```json" in json_match:
                json_match = json_match.split("```json")[1].split("```")[0]
            elif "```" in json_match:
                json_match = json_match.split("```")[1].split("```")[0]
            return json.loads(json_match.strip())
        except Exception:
            return {"error": "Failed to parse JSON", "raw": raw}


class AgentSwarm:
    """Multi-agent analysis pipeline for NZ criminal defence."""
    
    def __init__(self, llm_client: Optional[OllamaLLMClient] = None, rag_engine=None):
        self.llm_client = llm_client or OllamaLLMClient()
        self.rag_engine = rag_engine
        self.parser = DisclosureParser(llm_client=self.llm_client)
        self.fact_sheet_builder = FactSheetBuilder()
        from core.issue_spotter import IssueSpotter
        self.issue_spotter = IssueSpotter(llm_client=self.llm_client)
        self._last_audit: Optional[Any] = None
    
    def analyse(self, raw_text: str, extra_collections: Optional[List[str]] = None) -> SynthesizedReport:
        """Run full 6-agent pipeline with parallel KC execution.

        Args:
            raw_text: Disclosure text to analyse.
            extra_collections: Optional list of collection names (e.g. uploaded
                documents) to include in RAG retrieval.
        """
        start_time = time.time()
        
        # Agent 1: Parser (fast, no LLM)
        parsed = self.parser.parse(raw_text)
        parsed_dict = self.parser.to_dict(parsed)

        # Build anchored fact sheet
        fact_sheet = self.fact_sheet_builder.build(parsed, raw_text, source_name="disclosure.txt")
        print(f"[AGENT_SWARM] fact_sheet warrants={len(fact_sheet.warrants)} officers={list(fact_sheet.officers.keys())} admissions={len(fact_sheet.admissions)}")

        # Spot the strongest defence theory
        issue_result = self.issue_spotter.spot(
            fact_sheet,
            primary_charge=parsed_dict.get("primary_charge") or {},
            legal_sources=[],
        )
        print(f"[AGENT_SWARM] central_theory={issue_result.central_theory}")

        # Agent 2: QueryGen (1 LLM call)
        queries = self._run_querygen(parsed)
        
        # RAG Retrieval
        rag_results, source_results = self._run_rag_retrieval(queries, extra_collections=extra_collections)
        
        # Extract only the charge-relevant text before sending to the LLMs. Full
        # disclosures often contain long background investigations (burglary,
        # trailer theft, etc.) that distract the model from the actual charge.
        primary_charge = parsed_dict.get("primary_charge") or {}
        print(f"[AGENT_SWARM] raw_text length={len(raw_text)}, primary_charge={primary_charge}")
        raw_text_for_prompt = self.parser.extract_charge_focused_text(raw_text, primary_charge, max_chars=40_000)
        if not raw_text_for_prompt:
            print("[AGENT_SWARM] charge-focused extraction returned empty; falling back to keyword-only extraction")
            raw_text_for_prompt = self.parser.extract_charge_focused_text(raw_text, None, max_chars=50_000)
        if not raw_text_for_prompt:
            print("[AGENT_SWARM] keyword extraction also empty; falling back to raw text head")
            raw_text_for_prompt = raw_text[:50_000]

        # Pull the highest-value defence facts to the top so the KCs cannot miss them.
        fact_snippets = self.parser.extract_defence_fact_snippets(raw_text_for_prompt, max_chars=8_000)
        print(f"[AGENT_SWARM] fact_snippets length={len(fact_snippets)}, preview={fact_snippets[:300]!r}")
        if fact_snippets:
            raw_text_for_prompt = (
                "KEY DEFENCE FACTS FROM THE DISCLOSURE (prioritise these in your analysis):\n\n"
                + fact_snippets
                + "\n\n--- FULL CHARGE-FOCUSED DISCLOSURE TEXT ---\n\n"
                + raw_text_for_prompt
            )

        print(f"[AGENT_SWARM] raw_text_for_prompt length={len(raw_text_for_prompt)}, contains 'gbl'={'gbl' in raw_text_for_prompt.lower()}, contains 'burglary'={'burglary' in raw_text_for_prompt.lower()}")

        # Agents 3-8: Run six KCs in parallel, but throttle to 2 concurrent
        # calls to avoid exhausting the RTX 3090's VRAM.
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            strat_future = executor.submit(self._run_strategist, parsed_dict, rag_results, raw_text_for_prompt, fact_sheet, issue_result)
            evid_future = executor.submit(self._run_evidential, parsed_dict, rag_results, raw_text_for_prompt, fact_sheet, issue_result)
            rights_future = executor.submit(self._run_rights, parsed_dict, rag_results, raw_text_for_prompt, fact_sheet, issue_result)
            admissions_future = executor.submit(self._run_admissions, parsed_dict, rag_results, raw_text_for_prompt, fact_sheet, issue_result)
            cross_exam_future = executor.submit(self._run_cross_exam, parsed_dict, rag_results, raw_text_for_prompt, fact_sheet, issue_result)
            disclosure_forensic_future = executor.submit(self._run_disclosure_forensic, parsed_dict, rag_results, raw_text_for_prompt, fact_sheet, issue_result)

            strategist_output = strat_future.result()
            evidential_output = evid_future.result()
            rights_output = rights_future.result()
            admissions_output = admissions_future.result()
            cross_exam_output = cross_exam_future.result()
            disclosure_forensic_output = disclosure_forensic_future.result()

        print(f"[AGENT_SWARM] KC output lengths: strategist={len(strategist_output)}, evidential={len(evidential_output)}, rights={len(rights_output)}, admissions={len(admissions_output)}, cross_exam={len(cross_exam_output)}, disclosure_forensic={len(disclosure_forensic_output)}")

        # Agent 9: Orchestrator (synthesises all KC outputs)
        report = self._run_orchestrator(
            strategist_output, evidential_output, rights_output,
            admissions_output, cross_exam_output, disclosure_forensic_output,
            raw_text_for_prompt, primary_charge, fact_sheet, issue_result
        )

        # Fallback: if the Orchestrator left sections empty or wrote the
        # placeholder "No ... returned", populate them directly from the KC outputs.
        self._apply_fallbacks(
            report, raw_text_for_prompt,
            strategist_output, evidential_output, rights_output,
            admissions_output, cross_exam_output, disclosure_forensic_output,
            primary_charge
        )

        # Agent 7: Citation Auditor (verify final report against sources)
        report = self._audit_report(report, source_results)

        # Final cleanup: ensure date, labels, and other cosmetic fixes survive
        # any auditor rewrites.
        self._sanitize_report_output(report, primary_charge=primary_charge)
        
        elapsed = round(time.time() - start_time, 2)
        print(f"Pipeline completed in {elapsed}s")
        
        return report

    def _audit_report(self, report: SynthesizedReport, sources: List[Any]) -> SynthesizedReport:
        """Run citation audit on the final orchestrator report."""
        if not self.rag_engine or not sources:
            return report

        try:
            auditor = getattr(self.rag_engine, "citation_auditor", None)
            if not auditor:
                return report

            # Combine all report sections into text for auditing
            report_text = "\n\n".join([
                report.executive_summary,
                report.charge_and_legislative_framework,
                report.summary_of_evidence,
                report.assessment_of_prosecution_case,
                report.elements_of_the_offence,
                report.defence_strategies,
                report.instructions_to_counsel_pre_trial,
                report.evidentiary_issues_to_raise,
                report.conclusion,
            ])

            audit = auditor.audit(report_text, sources, "multi-agent disclosure analysis")
            self._last_audit = audit
            if not audit or not audit.unverified_citations:
                return report

            # Prefer the auditor's corrected text if it removes bad citations.
            corrected = getattr(audit, "corrected_response", None)
            if corrected and isinstance(corrected, str) and len(corrected) > 200:
                corrected_sections = self._extract_markdown_sections(corrected)
                if corrected_sections:
                    def pick(*names):
                        for n in names:
                            if n in corrected_sections:
                                return self._clean_field(corrected_sections[n])
                        return ""
                    report.executive_summary = pick("executive summary", "executive_summary") or report.executive_summary
                    report.charge_and_legislative_framework = pick("charge and legislative framework", "charge_and_legislative_framework") or report.charge_and_legislative_framework
                    report.summary_of_evidence = pick("summary of evidence", "summary_of_evidence") or report.summary_of_evidence
                    report.assessment_of_prosecution_case = pick("assessment of prosecution case", "assessment_of_prosecution_case") or report.assessment_of_prosecution_case
                    report.evidence_analysis = pick("evidence analysis", "evidence_analysis") or report.evidence_analysis
                    report.elements_of_the_offence = pick("elements of the offence", "elements_of_the_offence", "elements of offence") or report.elements_of_the_offence
                    report.defence_strategies = pick("defence strategies", "defence_strategies") or report.defence_strategies
                    report.instructions_to_counsel_pre_trial = pick("instructions to counsel pre-trial", "instructions_to_counsel_pre_trial", "instructions to counsel") or report.instructions_to_counsel_pre_trial
                    report.pre_trial_instructions_for_lawyer = pick("pre-trial instructions for lawyer", "pre_trial_instructions_for_lawyer", "pre-trial instructions") or report.pre_trial_instructions_for_lawyer
                    report.evidentiary_issues_to_raise = pick("evidentiary issues to raise", "evidentiary_issues_to_raise") or report.evidentiary_issues_to_raise
                    report.conclusion = pick("conclusion") or report.conclusion
                    report.conclusion_and_risk_assessment = pick("conclusion and risk assessment", "conclusion_and_risk_assessment") or report.conclusion_and_risk_assessment
                    report.disclaimer = pick("disclaimer") or report.disclaimer

            # Strip any remaining invented case citations or wrong NZBORA s 8 from
            # the report body so the final brief never relies on hallucinated authority.
            self._strip_unverified_citations_from_report(report, audit.unverified_citations)

            # Sanitise the unverified list that is exposed to the UI: never display
            # an invented case name as if it were a real citation.
            audit.unverified_citations = [
                self._sanitize_citation_display(c) for c in audit.unverified_citations
            ]

            # Drop any auditor hallucinations: an "unverified citation" must actually
            # appear somewhere in the report text.
            report_text = " ".join(
                str(getattr(report, f, "") or "")
                for f in [
                    "title_block", "table_of_contents", "executive_summary",
                    "charge_and_legislative_framework", "summary_of_evidence",
                    "assessment_of_prosecution_case", "evidence_analysis",
                    "elements_of_the_offence", "defence_strategies",
                    "cross_examination_priorities", "disclosure_and_forensic_gaps",
                    "instructions_to_counsel_pre_trial", "pre_trial_instructions_for_lawyer",
                    "evidentiary_issues_to_raise", "conclusion",
                    "conclusion_and_risk_assessment", "disclaimer"
                ]
            )
            audit.unverified_citations = [
                c for c in audit.unverified_citations
                if c.lower() in report_text.lower()
            ]

            # If filtering removed all unverified citations, reset risk to zero.
            if not audit.unverified_citations:
                audit.hallucination_risk = 0.0

            warning = self._build_citation_warning(audit)
            # Append warning to conclusion/risk assessment
            report.conclusion_and_risk_assessment = (
                (report.conclusion_and_risk_assessment or "").strip()
                + "\n\n"
                + warning
            )
            # Keep legacy field in sync
            report.risk_assessment = report.conclusion_and_risk_assessment
        except Exception as e:
            print(f"[Citation audit warning] {e}")

        return report

    def _strip_unverified_citations_from_report(self, report: SynthesizedReport, citations: List[str]) -> None:
        """Remove invented case citations and incorrect statute refs from report text."""
        if not citations:
            return

        fields = [
            "executive_summary", "charge_and_legislative_framework",
            "summary_of_evidence", "assessment_of_prosecution_case",
            "evidence_analysis", "elements_of_the_offence",
            "defence_strategies", "cross_examination_priorities",
            "disclosure_and_forensic_gaps", "instructions_to_counsel_pre_trial",
            "pre_trial_instructions_for_lawyer", "evidentiary_issues_to_raise",
            "conclusion", "conclusion_and_risk_assessment", "disclaimer",
            "title_block", "table_of_contents",
        ]

        for citation in citations:
            low = citation.lower()
            # Only strip case citations and known wrong statute references.
            is_case = any(marker in low for marker in [
                " v ", "nzca", "nzhc", "nzlr", "nzsc", "[20", "[19"
            ])
            is_wrong_statute = low in ("s 8 nzbora", "s.8 nzbora", "section 8 nzbora", "new zealand bill of rights act 1990, s 8")
            if not (is_case or is_wrong_statute):
                continue

            for field in fields:
                text = getattr(report, field, None) or ""
                if not text:
                    continue
                # Remove the citation string (case-insensitive).
                pattern = re.escape(citation)
                new_text = re.sub(pattern, "[authority not verified in retrieved sources]", text, flags=re.IGNORECASE)
                # Clean up empty parentheses left behind.
                new_text = re.sub(r"\(\s*\[authority not verified in retrieved sources\]\s*\)", "", new_text)
                new_text = re.sub(r"\[authority not verified in retrieved sources\]\s*\)", ")", new_text)
                new_text = re.sub(r"\(\s*\[authority not verified in retrieved sources\]", "", new_text)
                setattr(report, field, new_text)

    def _sanitize_citation_display(self, citation: str) -> str:
        """Replace invented case names in warnings with a safe placeholder."""
        if not citation:
            return citation
        low = citation.lower()
        is_case = any(marker in low for marker in [
            " v ", "nzca", "nzhc", "nzlr", "nzsc", "[20", "[19"
        ])
        if is_case:
            return "[unverified case citation — name removed]"
        return citation

    def _build_citation_warning(self, audit: Any) -> str:
        """Build a human-readable citation warning."""
        lines = ["⚠️  CITATION AUDIT WARNING"]
        lines.append(f"Hallucination risk: {getattr(audit, 'hallucination_risk', 0.0):.0%}")
        unverified = getattr(audit, "unverified_citations", [])
        if unverified:
            lines.append(f"Unverified citations ({len(unverified)}):")
            for c in unverified[:10]:
                lines.append(f"  • {c}")
        lines.append("Do not rely on unverified legal authority without independent confirmation.")
        return "\n".join(lines)
    
    def _run_querygen(self, parsed: ParsedDisclosure) -> List[str]:
        if not parsed.charges:
            return ["New Zealand criminal procedure overview", "defence rights NZBORA"]
        
        prompt = PROMPTS["querygen_user"](parsed.charges, parsed.raw_text[:500])
        system = PROMPTS["querygen_system"]
        
        result = self.llm_client.generate_json(prompt, system, temperature=0.1, max_tokens=2000)
        
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "queries" in result:
            return result["queries"]
        else:
            queries = []
            for charge in parsed.charges:
                queries.append(f"{charge['offense']} {charge['statute']} elements New Zealand")
                queries.append(f"{charge['offense']} defence New Zealand case law")
                queries.append(f"{charge['offense']} sentencing range New Zealand")
            return queries
    
    def _run_rag_retrieval(self, queries: List[str], extra_collections: Optional[List[str]] = None) -> tuple[str, List[Any]]:
        """Retrieve legal authority and return formatted text plus raw results."""
        if self.rag_engine is None:
            return "[RAG engine not available — using general legal knowledge]", []
        
        # Build the set of collections to search. Start with the engine's loaded
        # collections, then explicitly include any uploaded-document collections
        # (user_uploads and temp_session_*) that exist in ChromaDB.
        search_collections: set = set()
        try:
            search_collections.update(getattr(self.rag_engine, "collections", {}).keys())
        except Exception:
            pass

        try:
            client = getattr(self.rag_engine, "client", None)
            if client:
                search_collections.update({c.name for c in client.list_collections()})
        except Exception:
            pass

        target_collections: List[str] = []
        # Prioritise uploaded documents from the current session
        for c in sorted(search_collections):
            if c.startswith("temp_session_") and c not in target_collections:
                target_collections.append(c)
        # Core legal collections
        for c in ["nz_legislation", "nz_case_law", "nz_police_manual"]:
            if c in search_collections and c not in target_collections:
                target_collections.append(c)
        # Any extras passed by the caller (e.g. a specific temp session or,
        # for staff, the user_uploads reference collection)
        if extra_collections:
            for c in extra_collections:
                if c not in target_collections:
                    target_collections.append(c)

        if not target_collections:
            target_collections = None  # fall back to engine default
        
        all_results: List[Any] = []
        formatted_parts: List[str] = []
        seen_docs: set = set()
        for query in queries[:3]:
            try:
                results = self.rag_engine.search(query=query, collections=target_collections, top_k=3)
                for r in results:
                    all_results.append(r)
                    title = r.metadata.get('title') or r.metadata.get('filename') or r.metadata.get('source', 'Unknown')
                    category = r.metadata.get('category', 'unknown')
                    snippet = r.document[:200].strip().replace("\n", " ")
                    key = (category, title, snippet)
                    if key in seen_docs:
                        continue
                    seen_docs.add(key)
                    formatted_parts.append(f"[{category.upper()} - {title}] {snippet}")
            except Exception as e:
                formatted_parts.append(f"[Search error for '{query}']: {e}")
        
        return "\n\n".join(formatted_parts) if formatted_parts else "[No RAG results retrieved]", all_results
    
    def _run_strategist(self, parsed_dict: Dict, rag_results: str, raw_text: str = "", fact_sheet=None, issue_result=None) -> str:
        prompt = PROMPTS["strategist_user"](parsed_dict, rag_results, raw_text=raw_text, fact_sheet=fact_sheet, issue_result=issue_result)
        system = PROMPTS["strategist_system"]
        return self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=4000)

    def _run_evidential(self, parsed_dict: Dict, rag_results: str, raw_text: str = "", fact_sheet=None, issue_result=None) -> str:
        prompt = PROMPTS["evidential_user"](parsed_dict, rag_results, raw_text=raw_text, fact_sheet=fact_sheet, issue_result=issue_result)
        system = PROMPTS["evidential_system"]
        return self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=4000)

    def _run_rights(self, parsed_dict: Dict, rag_results: str, raw_text: str = "", fact_sheet=None, issue_result=None) -> str:
        prompt = PROMPTS["rights_user"](parsed_dict, rag_results, raw_text=raw_text, fact_sheet=fact_sheet, issue_result=issue_result)
        system = PROMPTS["rights_system"]
        return self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=4000)

    def _run_admissions(self, parsed_dict: Dict, rag_results: str, raw_text: str = "", fact_sheet=None, issue_result=None) -> str:
        prompt = PROMPTS["admissions_user"](parsed_dict, rag_results, raw_text=raw_text, fact_sheet=fact_sheet, issue_result=issue_result)
        system = PROMPTS["admissions_system"]
        return self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=4000)

    def _run_cross_exam(self, parsed_dict: Dict, rag_results: str, raw_text: str = "", fact_sheet=None, issue_result=None) -> str:
        prompt = PROMPTS["cross_exam_user"](parsed_dict, rag_results, raw_text=raw_text, fact_sheet=fact_sheet, issue_result=issue_result)
        system = PROMPTS["cross_exam_system"]
        return self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=4000)

    def _run_disclosure_forensic(self, parsed_dict: Dict, rag_results: str, raw_text: str = "", fact_sheet=None, issue_result=None) -> str:
        prompt = PROMPTS["disclosure_forensic_user"](parsed_dict, rag_results, raw_text=raw_text, fact_sheet=fact_sheet, issue_result=issue_result)
        system = PROMPTS["disclosure_forensic_system"]
        return self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=4000)

    def _run_orchestrator(self, strategist: str, evidential: str, rights: str,
                          admissions: str, cross_exam: str, disclosure_forensic: str,
                          raw_text: str = "", primary_charge: Optional[Dict] = None, fact_sheet=None, issue_result=None) -> SynthesizedReport:
        prompt = PROMPTS["orchestrator_user"](
            strategist, evidential, rights,
            admissions, cross_exam, disclosure_forensic,
            raw_text=raw_text, primary_charge=primary_charge, fact_sheet=fact_sheet, issue_result=issue_result
        )
        system = PROMPTS["orchestrator_system"]

        raw_output = self.llm_client.generate(prompt, system, temperature=0.1, max_tokens=12000)

        return self._parse_orchestrator_output(raw_output)
    
    def _parse_orchestrator_output(self, raw: str) -> SynthesizedReport:
        report = SynthesizedReport()
        sections = self._extract_markdown_sections(raw)

        def get_section(*names: str) -> str:
            for name in names:
                if name in sections:
                    return self._clean_field(sections[name])
            return ""

        # New legal-brief sections
        report.title_block = get_section("title block", "title_block")
        report.table_of_contents = get_section("table of contents", "table_of_contents")
        report.executive_summary = get_section("executive summary", "executive_summary")
        report.charge_and_legislative_framework = get_section(
            "charge and legislative framework", "charge_and_legislative_framework"
        )
        report.summary_of_evidence = get_section("summary of evidence", "summary_of_evidence")
        report.assessment_of_prosecution_case = get_section(
            "assessment of prosecution case", "assessment_of_prosecution_case"
        )
        # Keep legacy evidence_analysis field populated for older UIs.
        report.evidence_analysis = get_section("evidence analysis", "evidence_analysis")
        if not report.evidence_analysis and (report.summary_of_evidence or report.assessment_of_prosecution_case):
            parts = [report.summary_of_evidence, report.assessment_of_prosecution_case]
            report.evidence_analysis = "\n\n".join(p for p in parts if p)
        report.elements_of_the_offence = get_section(
            "elements of the offence", "elements_of_the_offence", "elements of offence",
            "elements the prosecution must prove", "elements_the_prosecution_must_prove"
        )
        report.defence_strategies = get_section(
            "defence strategies", "defence_strategies",
            "defence strategies and options", "defence_strategies_and_options"
        )
        report.cross_examination_priorities = get_section(
            "cross examination priorities", "cross_examination_priorities",
            "cross-examination priorities", "cross examination"
        )
        report.disclosure_and_forensic_gaps = get_section(
            "disclosure and forensic gaps", "disclosure_and_forensic_gaps",
            "disclosure forensic gaps", "forensic gaps"
        )
        report.instructions_to_counsel_pre_trial = get_section(
            "instructions to counsel pre-trial", "instructions_to_counsel_pre_trial",
            "instructions to counsel pre trial", "instructions to counsel"
        )
        report.pre_trial_instructions_for_lawyer = get_section(
            "pre-trial instructions for lawyer",
            "pre_trial_instructions_for_lawyer",
            "pre trial instructions for lawyer",
            "pre-trial instructions",
        )
        if not report.instructions_to_counsel_pre_trial:
            report.instructions_to_counsel_pre_trial = report.pre_trial_instructions_for_lawyer
        report.evidentiary_issues_to_raise = get_section(
            "evidentiary issues to raise", "evidentiary_issues_to_raise"
        )
        report.conclusion = get_section("conclusion")
        report.conclusion_and_risk_assessment = get_section(
            "conclusion and risk assessment", "conclusion_and_risk_assessment"
        )
        if not report.conclusion_and_risk_assessment:
            report.conclusion_and_risk_assessment = report.conclusion
        report.disclaimer = get_section("disclaimer")

        # Fallback to legacy sections if the new ones are absent
        if not report.charge_and_legislative_framework:
            report.charge_and_legislative_framework = get_section("charge analysis", "charge_analysis")
        if not report.evidence_analysis:
            report.evidence_analysis = get_section(
                "summary of facts review", "summary_of_facts_review",
                "police conduct assessment", "police_conduct_assessment"
            )
        if not report.conclusion_and_risk_assessment:
            report.conclusion_and_risk_assessment = get_section("risk assessment", "risk_assessment")
        if not report.pre_trial_instructions_for_lawyer:
            report.pre_trial_instructions_for_lawyer = get_section(
                "options and recommendations", "options_and_recommendations"
            )

        # Legacy fields kept for backward compatibility
        report.disclosure_overview = get_section("disclosure overview", "disclosure_overview")
        report.charge_analysis = report.charge_and_legislative_framework
        report.summary_of_facts_review = report.evidence_analysis
        report.police_conduct_assessment = get_section("police conduct assessment", "police_conduct_assessment")
        report.further_disclosure_required = get_section("further disclosure required", "further_disclosure_required")
        report.bail_analysis = get_section("bail analysis", "bail_analysis")
        report.options_and_recommendations = report.pre_trial_instructions_for_lawyer
        report.expert_consensus_and_divergence = get_section(
            "expert consensus and divergence", "expert_consensus_and_divergence"
        )
        report.risk_assessment = report.conclusion_and_risk_assessment

        if not report.executive_summary and raw:
            report.executive_summary = self._clean_field(raw[:500] + "...")

        return report
    
    def _clean_field(self, text: str) -> str:
        """Strip markdown heading prefixes and clean whitespace."""
        if not text:
            return ""
        cleaned = re.sub(r'^[#]{1,6}\s*', '', text.strip())
        cleaned = re.sub(r'^\*\*', '', cleaned); cleaned = re.sub(r'\*\*', '', cleaned); cleaned = re.sub(r'^[^:]+:\s*', '', cleaned)
        cleaned = re.sub(r'^---+\s*$', '', cleaned, flags=re.MULTILINE).strip(); return cleaned

    def _find_section_in_text(self, text: str, heading_candidates: List[str]) -> str:
        """Find a section in a KC output by heading (numbered, markdown, or plain)."""
        if not text:
            return ""
        lines = text.splitlines()
        start_idx = None
        for i, line in enumerate(lines):
            # Strip leading numbering/markdown/bullets for matching
            clean = re.sub(r'^[#\s\d\.\)\-\*]+', '', line).strip().lower()
            for cand in heading_candidates:
                if clean == cand.lower() or clean.startswith(cand.lower()):
                    start_idx = i
                    break
            if start_idx is not None:
                break
        if start_idx is None:
            return ""
        content_lines = []
        for line in lines[start_idx + 1:]:
            stripped = line.strip()
            if not stripped:
                content_lines.append(stripped)
                continue
            # Stop at the next major heading: numbered section, markdown heading, or ALL CAPS heading
            if re.match(r'^(?:\d+\.\s|[A-Z]\.\s|#+\s|[A-Z][A-Z\s\-]{3,}[A-Z]\s*$)', stripped):
                break
            content_lines.append(stripped)
        return "\n".join(content_lines).strip()

    def _sections_are_duplicate(self, a: str, b: str, threshold: float = 0.7) -> bool:
        """Return True if section b is mostly a duplicate of section a."""
        if not a or not b:
            return False
        a_norm = re.sub(r'\s+', ' ', a.lower()).strip()
        b_norm = re.sub(r'\s+', ' ', b.lower()).strip()
        if len(a_norm) < 50 or len(b_norm) < 50:
            return False
        if b_norm in a_norm or a_norm in b_norm:
            return True
        a_tokens = set(a_norm.split())
        b_tokens = set(b_norm.split())
        if not a_tokens or not b_tokens:
            return False
        overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
        return overlap > threshold

    def _extract_court_from_text(self, text: str) -> Optional[str]:
        """Extract the court name from disclosure text."""
        if not text:
            return None
        match = re.search(r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*)\s+(District|High)\s+Court", text)
        if match:
            return f"{match.group(1).strip()} {match.group(2)} Court"
        return None

    def _apply_fallbacks(self, report: SynthesizedReport, raw_text: str,
                         strategist: str, evidential: str, rights: str,
                         admissions: str, cross_exam: str, disclosure_forensic: str,
                         primary_charge: Optional[Dict]) -> None:
        """Fill any report sections the Orchestrator left empty using KC outputs."""

        def is_empty(text: str) -> bool:
            return not text or text.strip().lower() in ("", "none", "n/a", "not stated")

        pc = primary_charge or {}
        defendant = pc.get("defendant_name") or pc.get("accused") or "the defendant"
        offense = pc.get("offense") or "the offence"
        statute = pc.get("statute") or "Not stated"
        court = pc.get("court") or self._extract_court_from_text(raw_text) or "Not stated"

        # Title block
        if is_empty(report.title_block):
            report.title_block = (
                "LEGAL ANALYSIS & DEFENCE INSTRUCTIONS\n"
                f"Court: {court}\n"
                f"Charge: {offense}\n"
                f"Statute: {statute}\n"
                f"Prepared: {date.today().strftime('%d %B %Y')}"
            )

        # Table of contents
        if is_empty(report.table_of_contents):
            report.table_of_contents = (
                "- Executive Summary\n"
                "- Charge and Legislative Framework\n"
                "- Summary of Evidence\n"
                "- Assessment of Prosecution Case\n"
                "- Elements the Prosecution Must Prove\n"
                "- Defence Strategies and Options\n"
                "- Cross-Examination Priorities\n"
                "- Disclosure and Forensic Gaps\n"
                "- Instructions to Counsel Pre-Trial\n"
                "- Evidentiary Issues to Raise\n"
                "- Conclusion\n"
                "- Disclaimer"
            )

        # Executive summary
        if is_empty(report.executive_summary):
            report.executive_summary = self._find_section_in_text(strategist, ["EXECUTIVE SUMMARY"]) or strategist[:1_200]

        # Charge framework
        if is_empty(report.charge_and_legislative_framework):
            report.charge_and_legislative_framework = (
                self._find_section_in_text(strategist, ["CHARGE AND LEGISLATIVE FRAMEWORK"])
                or f"Charge: {offense}\nStatute: {statute}"
            )

        # Reconstruct charge framework if the model output dropped key headings
        cf = report.charge_and_legislative_framework or ""
        if ("Relevant Legislation" not in cf and "Maximum Penalty" not in cf and "Elements" not in cf
                and "charge" in offense.lower()):
            max_pen = (primary_charge or {}).get("maximum_penalty") or "Not stated in charging document"
            report.charge_and_legislative_framework = (
                f"The Charge\n{offense}\n\n"
                f"Relevant Legislation:\n{statute}\n\n"
                f"Maximum Penalty:\n{max_pen}\n\n"
                f"Elements the Prosecution Must Prove:\n"
                f"1. Custody or control of the substance.\n"
                f"2. Knowledge that the substance was a controlled drug."
            )

        # Summary of evidence
        if is_empty(report.summary_of_evidence):
            report.summary_of_evidence = (
                self._find_section_in_text(evidential, ["PROSECUTION EVIDENCE STRENGTHS", "PROSECUTION EVIDENCE WEAKNESSES", "KEY FACTUAL DISPUTES"])
                or evidential[:2_000]
            )

        # Assessment of prosecution case
        if is_empty(report.assessment_of_prosecution_case) or self._sections_are_duplicate(report.summary_of_evidence, report.assessment_of_prosecution_case):
            assessment = self._find_section_in_text(evidential, ["PROSECUTION EVIDENCE STRENGTHS", "PROSECUTION EVIDENCE WEAKNESSES"])
            if not assessment:
                assessment = evidential[:2_000]
            report.assessment_of_prosecution_case = assessment

        # Elements the prosecution must prove
        if is_empty(report.elements_of_the_offence):
            report.elements_of_the_offence = (
                self._find_section_in_text(strategist, ["ELEMENT-BY-ELEMENT ASSESSMENT", "ELEMENT BY ELEMENT ASSESSMENT"])
                or self._find_section_in_text(evidential, ["ELEMENT-BY-ELEMENT SUFFICIENCY", "ELEMENT BY ELEMENT SUFFICIENCY"])
                or strategist[:1_500]
            )

        # Cosmetic: ensure elements section has a clear first heading for drug possession
        if report.elements_of_the_offence and "drug" in offense.lower():
            first_line = next((l for l in report.elements_of_the_offence.splitlines() if l.strip()), "")
            if first_line and not re.match(r'^(\s*Element\s*1\s*[:\-]|\s*\d+\.\s+|\s*Custody|\s*Possession)', first_line, re.IGNORECASE):
                report.elements_of_the_offence = (
                    "Element 1: Custody or Control of the Substance\n\n"
                    + report.elements_of_the_offence
                )

        # Defence strategies
        if is_empty(report.defence_strategies):
            report.defence_strategies = (
                self._find_section_in_text(strategist, ["DEFENCE STRATEGIES"])
                or strategist[1_500:5_000]
            )

        # Cross-examination priorities
        if is_empty(report.cross_examination_priorities):
            report.cross_examination_priorities = cross_exam[:4_000]

        # Disclosure and forensic gaps
        if is_empty(report.disclosure_and_forensic_gaps):
            report.disclosure_and_forensic_gaps = disclosure_forensic[:4_000]

        # Instructions to counsel pre-trial
        if is_empty(report.instructions_to_counsel_pre_trial):
            parts = []
            bail = self._find_section_in_text(strategist, ["BAIL AND PLEA TACTICS"])
            if bail:
                parts.append(bail)
            remedies = self._find_section_in_text(rights, ["RIGHTS BREACH REMEDIES", "REMEDIES"])
            if remedies:
                parts.append(remedies)
            steps = self._find_section_in_text(disclosure_forensic, ["PRACTICAL NEXT STEPS", "DISCLOSURE APPLICATIONS"])
            if steps:
                parts.append(steps)
            if not parts:
                parts = [strategist[-2_000:], disclosure_forensic[:2_000]]
            report.instructions_to_counsel_pre_trial = "\n\n".join(p for p in parts if p)[:4_000]

        # Evidentiary issues to raise
        if is_empty(report.evidentiary_issues_to_raise):
            report.evidentiary_issues_to_raise = (
                self._find_section_in_text(evidential, ["EVIDENTIARY ISSUES TO RAISE"])
                or rights[:2_000]
            )

        # Cosmetic fallback: ensure first Disclosure item has a title line
        if report.disclosure_and_forensic_gaps:
            first_line = next((l for l in report.disclosure_and_forensic_gaps.splitlines() if l.strip()), "")
            has_title = bool(re.match(r'^\s*(\d+\.|[A-Z][A-Za-z\s]{2,}:|Item\s+\d+|\-\s*[A-Z][A-Za-z\s]{2,}:)', first_line))
            if not has_title or re.match(r'^\s*-\s*Why it Matters', first_line, re.IGNORECASE):
                report.disclosure_and_forensic_gaps = "1. Missing Disclosure Item\n" + report.disclosure_and_forensic_gaps

        # Cosmetic fallback: ensure first Evidentiary Issue has a title line
        if report.evidentiary_issues_to_raise:
            first_line = next((l for l in report.evidentiary_issues_to_raise.splitlines() if l.strip()), "")
            has_title = bool(re.match(r'^\s*(\d+\.|[A-Z][A-Za-z\s]{2,}:|Issue\s+\d+|\-\s*[A-Z][A-Za-z\s]{2,}:)', first_line))
            is_just_basis = bool(re.match(r'^\s*(NZBORA\s+s\s*\d+|S\s+\d+\(?.\)?|Evidence Act|Search and Surveillance Act|Crimes Act| Misuse of Drugs Act)', first_line, re.IGNORECASE))
            if not has_title or is_just_basis or re.match(r'^\s*-\s*Legal Basis', first_line, re.IGNORECASE):
                report.evidentiary_issues_to_raise = "1. Evidentiary Issue\n" + report.evidentiary_issues_to_raise

        # Conclusion
        if is_empty(report.conclusion):
            report.conclusion = (
                self._find_section_in_text(strategist, ["CONCLUSION"])
                or strategist[-1_500:]
            )

        if is_empty(report.conclusion_and_risk_assessment):
            report.conclusion_and_risk_assessment = report.conclusion

        # Disclaimer
        if is_empty(report.disclaimer):
            report.disclaimer = (
                "This analysis is generated by AI and does not constitute legal advice. "
                "It should be reviewed by a qualified New Zealand lawyer before use in any legal proceeding."
            )

        # --- Formatting cleanups ---
        # Ensure title block fields are on separate lines
        if report.title_block and "\n" not in report.title_block:
            # Split before Charge/Statute/Prepared even if the Court label is missing
            report.title_block = re.sub(
                r'\s*(Charge:|Statute:|Prepared:)\s*',
                r'\n\1 ',
                report.title_block
            ).strip()
            if not report.title_block.startswith("Court:"):
                lines = report.title_block.splitlines()
                report.title_block = "Court: " + lines[0] + "\n" + "\n".join(lines[1:])

        # Ensure TOC items are on separate lines
        if report.table_of_contents and "\n" not in report.table_of_contents:
            report.table_of_contents = report.table_of_contents.replace(" - ", "\n- ").strip()

        # Ensure assessment has a Weaknesses subsection
        if report.assessment_of_prosecution_case and "## Weaknesses" not in report.assessment_of_prosecution_case:
            weaknesses = self._find_section_in_text(evidential, [
                "PROSECUTION EVIDENCE WEAKNESSES", "WEAKNESSES", "DEFENCE RESPONSES", "DEFENCE POSITION"
            ])
            if not weaknesses and rights:
                weaknesses = self._find_section_in_text(rights, ["RIGHTS BREACH REMEDIES", "WEAKNESSES"])
            if weaknesses:
                report.assessment_of_prosecution_case = (
                    report.assessment_of_prosecution_case.rstrip()
                    + "\n\n## Weaknesses\n\n"
                    + weaknesses
                )

        # ── Final output sanitisation ─────────────────────────────────────────
        self._sanitize_report_output(report, primary_charge=primary_charge)

    def _sanitize_report_output(
        self,
        report: SynthesizedReport,
        offense: str = "",
        primary_charge: Optional[Dict] = None,
    ) -> None:
        """Catch and correct common model output defects."""
        if not report:
            return

        today_str = date.today().strftime("%d %B %Y")
        pc = primary_charge or {}
        if not offense and pc.get("offense"):
            offense = pc["offense"]
        offense_lower = offense.lower()

        fields = [
            "title_block", "table_of_contents", "executive_summary",
            "charge_and_legislative_framework", "summary_of_evidence",
            "assessment_of_prosecution_case", "evidence_analysis",
            "elements_of_the_offence", "defence_strategies",
            "cross_examination_priorities", "disclosure_and_forensic_gaps",
            "instructions_to_counsel_pre_trial", "pre_trial_instructions_for_lawyer",
            "evidentiary_issues_to_raise", "conclusion",
            "conclusion_and_risk_assessment", "disclaimer",
        ]

        for field in fields:
            text = getattr(report, field, None) or ""
            if not text:
                continue

            # 1. Replace literal date placeholders
            text = re.sub(r"\[\s*today[''’]?s?\s+date\s*\]|\[\s*today\s*\]|\[\s*current\s+date\s*\]",
                          today_str, text, flags=re.IGNORECASE)

            # 2. Stamp out the wrong legal standard for drug possession
            if "drug" in offense_lower:
                text = re.sub(
                    r"knew\s*\(\s*or\s+ought\s+reasonably\s+to\s+have\s+known\s*\)",
                    "actually knew",
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    r"ought\s+reasonably\s+to\s+have\s+known",
                    "actually knew",
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    r"should\s+have\s+known",
                    "actually knew",
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    r"constructive\s+knowledge",
                    "actual knowledge",
                    text,
                    flags=re.IGNORECASE,
                )

            # 3. Remove rights-compliance ratings that leak into evidence sections
            if field == "assessment_of_prosecution_case":
                text = re.sub(
                    r"\n\s*Rating:\s*(?:COMPLIANT|MINOR CONCERN|SIGNIFICANT BREACH|FUNDAMENTAL BREACH)\s*",
                    "\n",
                    text,
                    flags=re.IGNORECASE,
                )
                text = re.sub(
                    r"\n\s*No significant breaches were identified[^\n]*(?:exclusion|stay|sentence reduction)[^\n]*",
                    "\n",
                    text,
                    flags=re.IGNORECASE,
                )

            setattr(report, field, text)

        # 4. Force the title-block date to today's date (models often hallucinate dates)
        if report.title_block:
            report.title_block = re.sub(
                r"(Prepared:\s*)(?:\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2}|\[[^\]]+\])",
                rf"\g<1>{today_str}",
                report.title_block,
                flags=re.IGNORECASE,
            )

        # 4b. Force title-block Charge and Statute to match the primary charge
        if report.title_block:
            if pc.get("offense"):
                report.title_block = re.sub(
                    r"(Charge:\s*)(.*?)\s*(\n|$)",
                    rf"\g<1>{pc['offense']}\3",
                    report.title_block,
                    count=1,
                    flags=re.IGNORECASE,
                )
            if pc.get("statute"):
                report.title_block = re.sub(
                    r"(Statute:\s*)(.*?)\s*(\n|$)",
                    rf"\g<1>{pc['statute']}\3",
                    report.title_block,
                    count=1,
                    flags=re.IGNORECASE,
                )

        # 5. Remove title-block duplication from Executive Summary
        if report.executive_summary and report.title_block:
            # If exec summary starts with court/charge/prepared lines, strip them
            tb_lines = [l.strip().lower() for l in report.title_block.splitlines() if l.strip()]
            es_lines = report.executive_summary.splitlines()
            drop_count = 0
            for line in es_lines:
                line_lower = line.strip().lower()
                if not line_lower:
                    drop_count += 1
                    continue
                if any(line_lower.startswith(prefix) for prefix in ["legal analysis", "court:", "charge:", "statute:", "prepared:"]) or line_lower in tb_lines:
                    drop_count += 1
                else:
                    break
            if drop_count > 0:
                report.executive_summary = "\n".join(es_lines[drop_count:]).strip()

        # 6. Burglary: remove "property was stolen" from elements
        if "burglary" in offense_lower and report.elements_of_the_offence:
            report.elements_of_the_offence = re.sub(
                r"\n\s*\d+\.\s*[Pp]roperty was stolen[^\n]*",
                "",
                report.elements_of_the_offence,
            )
            report.elements_of_the_offence = re.sub(
                r"^\s*\d+\.\s*[Pp]roperty was stolen[^\n]*\n?",
                "",
                report.elements_of_the_offence,
            )
            report.elements_of_the_offence = re.sub(r"\n{3,}", "\n\n", report.elements_of_the_offence).strip()

        # 7. Ensure Elements section starts with the correct numbered element heading
        if report.elements_of_the_offence:
            expected_elem1 = self._expected_element_1(offense_lower)
            first_line = next((l for l in report.elements_of_the_offence.splitlines() if l.strip()), "")
            if first_line and not re.match(r"^\s*\d+\.\s+", first_line):
                report.elements_of_the_offence = f"1. {expected_elem1}\n\n" + report.elements_of_the_offence
            elif first_line and not self._element_heading_matches_offense(first_line, offense_lower):
                # Model wrote the wrong element heading (e.g., drug element for a burglary charge)
                report.elements_of_the_offence = re.sub(
                    r"^\s*\d+\.\s+.*$",
                    f"1. {expected_elem1}",
                    report.elements_of_the_offence,
                    count=1,
                    flags=re.MULTILINE,
                )

        # 7b. Offence-specific corrections for common mislabelled element headings
        if report.elements_of_the_offence:
            report.elements_of_the_offence = self._correct_element_headings(
                report.elements_of_the_offence, offense_lower
            )

        # 7c. Ensure all element headings are sequentially numbered
        if report.elements_of_the_offence:
            report.elements_of_the_offence = self._renumber_elements(
                report.elements_of_the_offence, offense_lower
            )

        # 8. Ensure defence strategies are cleanly labelled A., B., C.
        if report.defence_strategies:
            report.defence_strategies = self._relabel_defence_strategies(report.defence_strategies)

        # 9. Cross-examination: drop non-police witnesses aggressively
        if report.cross_examination_priorities:
            report.cross_examination_priorities = self._filter_cross_exam_to_police(
                report.cross_examination_priorities
            )

        # 10. Better fallback titles for Disclosure Gaps / Evidentiary Issues
        if report.disclosure_and_forensic_gaps:
            first_line = next((l for l in report.disclosure_and_forensic_gaps.splitlines() if l.strip()), "")
            if re.match(r"^1\.\s*Missing Disclosure Item", first_line, re.IGNORECASE):
                report.disclosure_and_forensic_gaps = re.sub(
                    r"^1\.\s*Missing Disclosure Item",
                    "1. Chain-of-custody and handling records for seized exhibits",
                    report.disclosure_and_forensic_gaps,
                    count=1,
                    flags=re.IGNORECASE,
                )

        if report.evidentiary_issues_to_raise:
            first_line = next((l for l in report.evidentiary_issues_to_raise.splitlines() if l.strip()), "")
            if re.match(r"^1\.\s*Evidentiary Issue", first_line, re.IGNORECASE):
                report.evidentiary_issues_to_raise = re.sub(
                    r"^1\.\s*Evidentiary Issue",
                    "1. Reliability and voluntariness of any alleged admission",
                    report.evidentiary_issues_to_raise,
                    count=1,
                    flags=re.IGNORECASE,
                )
            # Remove a bare statute citation used as an issue title
            report.evidentiary_issues_to_raise = re.sub(
                r"^\s*\d+\.\s*(?:Crimes Act|Summary Offences Act|Evidence Act|Search and Surveillance Act|Misuse of Drugs Act|NZBORA)\s+[^\n]*(?:s\s*\d+).*\n(?=\s*[-•]\s*Legal Basis:)",
                "",
                report.evidentiary_issues_to_raise,
                flags=re.IGNORECASE | re.MULTILINE,
            )

        # 11. Ensure Weaknesses under Assessment is a numbered list
        if report.assessment_of_prosecution_case:
            # Normalise a bare "Weaknesses" heading to a markdown subheading
            report.assessment_of_prosecution_case = re.sub(
                r"(?im)^\s*Weaknesses\s*$",
                "## Weaknesses",
                report.assessment_of_prosecution_case,
            )
            if "## Weaknesses" in report.assessment_of_prosecution_case:
                parts = report.assessment_of_prosecution_case.split("## Weaknesses", 1)
                before = parts[0]
                after = parts[1]
                # Drop Rights-KC-style summary paragraphs
                after = re.sub(
                    r"\n\s*No significant breaches were identified[^\n]*(?:exclusion|stay|sentence reduction)[^\n]*",
                    "\n",
                    after,
                    flags=re.IGNORECASE,
                )
                non_empty_lines = [l for l in after.splitlines() if l.strip()]
                if non_empty_lines and not re.match(r"^\s*\d+\.\s+", non_empty_lines[0]):
                    after = self._number_weaknesses(after)
                report.assessment_of_prosecution_case = before + "## Weaknesses\n\n" + after

    def _number_weaknesses(self, text: str) -> str:
        """Convert bullet/paragraph weaknesses into a clean numbered list."""
        paragraphs = re.split(r"\n{2,}", text.strip())
        numbered = []
        count = 1
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            lines = para.splitlines()
            first = lines[0].strip()

            # Already numbered
            if re.match(r"^\d+\.\s+", first):
                numbered.append(para)
                continue

            # Bullet start
            if re.match(r"^[-•*]\s+", first):
                first = re.sub(r"^[-•*]\s+", "", first)
                para = first + "\n" + "\n".join(lines[1:])

            # Bold heading like **Chain of Custody Issues:**
            if re.match(r"^\*\*[^*]+\*\*", first):
                # Keep the bold heading as part of the numbered item
                pass

            numbered.append(f"{count}. {para}")
            count += 1
        return "\n\n".join(numbered)

    def _expected_element_1(self, offense_lower: str = "") -> str:
        """Return the correct first element heading for the offence type."""
        if "burglary" in offense_lower:
            return "The defendant entered a building or ship as a trespasser."
        if "theft" in offense_lower or "receiving" in offense_lower or "dishonest" in offense_lower:
            return "The defendant took or controlled property belonging to another."
        if "assault" in offense_lower:
            return "The defendant applied force to another person."
        return "The defendant had custody or control of the substance."

    def _element_heading_matches_offense(self, heading: str, offense_lower: str = "") -> bool:
        """Return True if an element heading is appropriate for the offence."""
        heading_lower = heading.lower()
        if "burglary" in offense_lower:
            return "trespasser" in heading_lower or "entered" in heading_lower or "entry" in heading_lower
        if "theft" in offense_lower or "receiving" in offense_lower or "dishonest" in offense_lower:
            return "property" in heading_lower or "took" in heading_lower or "controlled" in heading_lower
        if "assault" in offense_lower:
            return "force" in heading_lower
        if "drug" in offense_lower:
            return "custody" in heading_lower or "control" in heading_lower or "knew" in heading_lower
        return True

    def _correct_element_headings(self, text: str, offense_lower: str = "") -> str:
        """Replace clearly-wrong element headings that survive renumbering."""
        if "burglary" in offense_lower:
            # Replace a drug-possession heading if it appears as element 1
            text = re.sub(
                r"(?im)^\s*(\d+)\.\s*The defendant had custody or control of the substance\.?",
                r"1. The defendant entered a building or ship as a trespasser.",
                text,
            )
            # Drop any "property was stolen" element
            text = re.sub(
                r"(?im)^\s*\d+\.\s*[Pp]roperty was stolen[^\n]*\n?",
                "",
                text,
            )
        elif "drug" in offense_lower:
            text = re.sub(
                r"(?im)^\s*(\d+)\.\s*The defendant entered a building or ship as a trespasser\.?",
                r"1. The defendant had custody or control of the substance.",
                text,
            )
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _renumber_elements(self, text: str, offense_lower: str = "") -> str:
        """Ensure every element heading in the section is sequentially numbered."""
        lines = text.splitlines()
        # Common element-heading patterns
        element_patterns = [
            r"the defendant (?:had )?custody or control",
            r"the defendant (?:actually )?knew",
            r"the defendant entered a building or ship as a trespasser",
            r"the entry was with intent to commit",
            r"the defendant took or controlled property",
            r"the defendant applied force to another",
            r"the defendant (?:intentionally|deliberately)",
        ]
        # If this is a known offence, restrict to the expected element wording
        if "drug" in offense_lower:
            element_patterns = [
                r"the defendant (?:had )?custody or control",
                r"the defendant (?:actually )?knew",
            ]
        elif "burglary" in offense_lower:
            element_patterns = [
                r"the defendant entered a building or ship as a trespasser",
                r"the entry was with intent to commit",
            ]
        elif "theft" in offense_lower or "receiving" in offense_lower:
            element_patterns = [
                r"the defendant (?:took|controlled|dishonestly) (?:or )?",
                r"the property belonged to another",
            ]

        pattern = re.compile("^(\\s*)(" + "|".join(element_patterns) + ")", re.IGNORECASE)

        out = []
        elem_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                out.append(line)
                continue
            # Already numbered — extract the number and continue
            m = re.match(r"^(\s*)\d+\.\s+(.*)$", stripped)
            if m:
                elem_count += 1
                out.append(f"{elem_count}. {m.group(2)}")
                continue
            # Looks like an element heading but not numbered
            if pattern.match(stripped) and not re.match(r"^[-•*]", stripped):
                elem_count += 1
                out.append(f"{elem_count}. {stripped}")
                continue
            out.append(line)
        return "\n".join(out)

    def _filter_cross_exam_to_police(self, text: str) -> str:
        """Remove non-police witnesses from cross-examination priorities."""
        blocks = re.split(r"\n(?=Witness:|\*\*Witness:|[A-Z][a-z]+\s+[A-Z][a-z]+\s*\(|\d+\.\s+[A-Z])", text)
        police_blocks = []
        for block in blocks:
            stripped = block.strip()
            if not stripped:
                continue
            first_line = stripped.splitlines()[0]
            lower = first_line.lower()
            if any(marker in lower for marker in ["police", "constable", "detective", "sergeant", "seizing officer", "searching officer"]):
                police_blocks.append(block)
        if not police_blocks:
            return text
        return "\n\n".join(police_blocks)

    def _relabel_defence_strategies(self, text: str) -> str:
        """Relabel defence strategies as A., B., C. cleanly.

        Strips any existing stray letter labels, merges duplicate Strategy Name
        lines, and re-applies sequential A., B., C. labels.
        """
        if not text or not text.strip():
            return text

        lines = text.splitlines()

        # First pass: normalise letter labels into Strategy Name lines
        cleaned = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            # Bare letter label — drop it
            if re.match(r"^[A-H]\.\s*$", stripped):
                i += 1
                continue
            # "A. Strategy Name: Foo" -> "Strategy Name: Foo"
            m = re.match(r"^[A-H]\.\s+(Strategy\s*Name\s*:.*)$", stripped, re.IGNORECASE)
            if m:
                cleaned.append(m.group(1))
                i += 1
                continue
            # "A. Foo bar" -> "Strategy Name: Foo bar"
            if re.match(r"^[A-H]\.\s+", stripped):
                heading = re.sub(r"^[A-H]\.\s+", "", stripped)
                cleaned.append(f"Strategy Name: {heading}")
                i += 1
                continue
            cleaned.append(line)
            i += 1

        # Merge consecutive Strategy Name lines (allowing blank lines between
        # them): keep the last one, which is usually the descriptive heading.
        merged = []
        i = 0
        while i < len(cleaned):
            line = cleaned[i]
            stripped = line.strip()
            if re.match(r"^Strategy\s*Name\s*:", stripped, re.IGNORECASE):
                last = line
                j = i + 1
                while j < len(cleaned) and not cleaned[j].strip():
                    j += 1
                while j < len(cleaned) and re.match(r"^Strategy\s*Name\s*:", cleaned[j].strip(), re.IGNORECASE):
                    last = cleaned[j]
                    j += 1
                    while j < len(cleaned) and not cleaned[j].strip():
                        j += 1
                merged.append(last)
                i = j
            else:
                merged.append(line)
                i += 1
        cleaned = merged

        # Split into strategies at Strategy Name boundaries
        strategies = []
        current = []
        for line in cleaned:
            stripped = line.strip()
            if re.match(r"^Strategy\s*Name\s*:", stripped, re.IGNORECASE):
                if current:
                    strategies.append(current)
                current = [line]
            else:
                current.append(line)
        if current:
            strategies.append(current)

        # Emit with sequential labels
        labels = ["A.", "B.", "C.", "D.", "E.", "F.", "G.", "H."]
        out = []
        label_idx = 0
        for strat in strategies:
            if label_idx >= len(labels):
                break
            # Trim leading/trailing blank lines
            while strat and not strat[0].strip():
                strat.pop(0)
            while strat and not strat[-1].strip():
                strat.pop()
            if not strat:
                continue

            first = strat[0].strip()
            if not re.match(r"^Strategy\s*Name\s*:", first, re.IGNORECASE):
                strat[0] = f"Strategy Name: {first}"
            # Remove any stray letter prefix
            strat[0] = re.sub(r"^[A-H]\.\s*", "", strat[0])

            out.append(labels[label_idx])
            out.extend(strat)
            label_idx += 1

        return "\n".join(out)

    def _extract_markdown_sections(self, text: str) -> Dict[str, str]:
        """Extract sections from markdown with nested # handling."""
        sections = {}
        
        # Normalize nested hashes: '## # HEADING' -> '## HEADING'
        normalized = re.sub(r'#{2,6}\s*#\s*', '## ', text)
        
        # Split by heading markers (1-3 # followed by text)
        pattern = r'#{1,3}\s*(.+?)\n+(.*?)(?=\n#{1,3}\s|$)'
        matches = re.findall(pattern, normalized, re.DOTALL | re.IGNORECASE)
        
        for heading, content in matches:
            key = heading.strip().lower().replace(" ", "_")
            sections[key] = content.strip()
            key2 = heading.strip().lower()
            sections[key2] = content.strip()
        
        # Fallback: if no sections found, try line-by-line header detection
        if not sections:
            lines = text.split('\n')
            current_heading = None
            current_content = []
            
            for line in lines:
                header_match = re.match(r'#{1,6}\s*#?\s*(.+)', line.strip())
                if header_match:
                    if current_heading and current_content:
                        key = current_heading.lower().replace(" ", "_")
                        sections[key] = '\n'.join(current_content).strip()
                    current_heading = header_match.group(1).strip()
                    current_content = []
                elif current_heading:
                    current_content.append(line)
            
            if current_heading and current_content:
                key = current_heading.lower().replace(" ", "_")
                sections[key] = '\n'.join(current_content).strip()
        
        return sections

    def analyse_disclosure(self, raw_text: str, extra_collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Dict-returning wrapper for API compatibility.

        Args:
            raw_text: Disclosure text to analyse.
            extra_collections: Optional list of collection names (e.g. uploaded
                documents) to include in RAG retrieval.
        """
        report = self.analyse(raw_text, extra_collections=extra_collections)
        return {
            # New legal-brief sections
            "title_block": report.title_block,
            "table_of_contents": report.table_of_contents,
            "executive_summary": report.executive_summary,
            "charge_and_legislative_framework": report.charge_and_legislative_framework,
            "summary_of_evidence": report.summary_of_evidence,
            "assessment_of_prosecution_case": report.assessment_of_prosecution_case,
            "evidence_analysis": report.evidence_analysis,
            "elements_of_the_offence": report.elements_of_the_offence,
            "defence_strategies": report.defence_strategies,
            "cross_examination_priorities": report.cross_examination_priorities,
            "disclosure_and_forensic_gaps": report.disclosure_and_forensic_gaps,
            "instructions_to_counsel_pre_trial": report.instructions_to_counsel_pre_trial,
            "pre_trial_instructions_for_lawyer": report.pre_trial_instructions_for_lawyer,
            "evidentiary_issues_to_raise": report.evidentiary_issues_to_raise,
            "conclusion": report.conclusion,
            "conclusion_and_risk_assessment": report.conclusion_and_risk_assessment,
            "disclaimer": report.disclaimer,
            # Legacy sections retained for backward compatibility
            "disclosure_overview": report.disclosure_overview,
            "charge_analysis": report.charge_analysis,
            "summary_of_facts_review": report.summary_of_facts_review,
            "police_conduct_assessment": report.police_conduct_assessment,
            "further_disclosure_required": report.further_disclosure_required,
            "bail_analysis": report.bail_analysis,
            "options_and_recommendations": report.options_and_recommendations,
            "expert_consensus_and_divergence": report.expert_consensus_and_divergence,
            "risk_assessment": report.risk_assessment,
            # Citation audit metadata
            "audit_report": getattr(self._last_audit, "audit_report", "") if self._last_audit else "",
            "metadata": {
                "hallucination_risk": getattr(self._last_audit, "hallucination_risk", 0.0) if self._last_audit else 0.0,
                "unverified_citations": getattr(self._last_audit, "unverified_citations", []) if self._last_audit else [],
                "verified_citations": getattr(self._last_audit, "verified_citations", []) if self._last_audit else [],
            },
            "processing_time_seconds": 0.0,
            "expert_count": 6,
            "success": True,
            "message": "Analysis complete",
        }
