

def _strip_ollama_unsupported_options(options):
    if not isinstance(options, dict):
        return {}
    options = dict(options)
    for key in ("mirostat", "mirostat_eta", "mirostat_tau", "tfs_z"):
        options.pop(key, None)
    return {k: v for k, v in options.items() if v is not None}


#!/usr/bin/env python3
"""
NZ Legal RAG Engine
Core retrieval and generation engine for legal research
"""

import os
import time
import json
import re
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import chromadb
from chromadb.config import Settings
from langchain_ollama import OllamaEmbeddings
from langchain_ollama import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter

from core.citation_guard import CitationGuard
from core.parser import DisclosureParser
from core.agents.intake_agent import CaseIntakeAgent, IntakeResult
from core.agents.defence_analyst import DefenceAnalyst
from core.agents.citation_auditor import CitationAuditor, AuditResult
from core.agents.defence_strategist import DefenceStrategist, StrategyResult
from core.agents.synthesis_agent import SynthesisAgent, SynthesisResult

@dataclass
class SearchResult:
    document: str
    metadata: Dict[str, Any]
    distance: float
    relevance: float

@dataclass
class LegalAnalysis:
    query: str
    answer: str
    citations: List[str]
    sources: List[SearchResult]
    confidence: float
    analysis_type: str
    # New multi-agent fields (backward-compatible defaults)
    executive_summary: str = ""
    audit_report: str = ""
    strategic_notes: str = ""
    confidence_breakdown: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    agent_trace: Dict[str, Any] = field(default_factory=dict)


class NZLegalRAG:
    """
    New Zealand Legal RAG System
    
    Features:
    - Multi-collection search (legislation, case law, police manual)
    - Legal element extraction
    - Citation tracking
    - Confidence scoring
    """
    
    COLLECTIONS = {
        "nz_legislation": "NZ Legislation",
        "nz_case_law": "NZ Case Law",
        "nz_police_manual": "NZ Police Manual",
        "confidential": "Confidential Documents (Local)"
    }
    
    def __init__(self, 
                 db_path: str = os.getenv("CHROMA_DB_PATH", "/workspace/chroma_db_fresh"),
                 embedding_model: str = os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest"),
                 llm_model: str = "deepseek-v3:latest",
                 use_local_llm: bool = True):
        self.db_path = Path(db_path)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(model=embedding_model, num_gpu=0)
        
        # Initialize LLM
        if use_local_llm:
            self.llm = OllamaLLM(
                model=llm_model,
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.15")),
                num_ctx=int(os.getenv("LLM_NUM_CTX", "16384")),
                num_predict=int(os.getenv("LLM_NUM_PREDICT", "4096"))
            )
        else:
            self.llm = None
        
        # Agent pipeline (full multi-agent architecture)
        self.intake_agent = CaseIntakeAgent(self.llm)
        self.defence_analyst = DefenceAnalyst(self.llm)
        self.citation_auditor = CitationAuditor(self.llm, search_callback=self.search)
        self.defence_strategist = DefenceStrategist(self.llm)
        self.synthesis_agent = SynthesisAgent()
        
        # Legacy citation verification guard (kept as fallback)
        self.citation_guard = CitationGuard()
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1500,
            chunk_overlap=150,
            separators=["\n\n", "\nSection", "\n[", ". ", " ", ""]
        )
        
        # Load collections
        self.collections = self._load_collections()
    
    def _load_collections(self) -> Dict[str, Any]:
        """Load available ChromaDB collections"""
        collections = {}
        
        for collection_name in self.COLLECTIONS.keys():
            try:
                collection = self.client.get_collection(collection_name)
                collections[collection_name] = collection
            except Exception:
                # Collection doesn't exist yet
                pass
        
        return collections
    
    def search(self, 
               query: str,
               collections: Optional[List[str]] = None,
               filters: Optional[Dict] = None,
               top_k: int = 10) -> List[SearchResult]:
        """
        Search across legal databases
        
        Args:
            query: Search query
            collections: List of collections to search (None = all)
            filters: Metadata filters
            top_k: Number of results to return
        """
        if collections is None:
            collections = list(self.collections.keys())
        
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        all_results = []
        
        # Search each collection
        for collection_name in collections:
            if collection_name not in self.collections:
                continue
            
            collection = self.collections[collection_name]
            
            # Build where filter
            where_filter = self._build_where_filter(filters, collection_name)
            
            try:
                results = collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, 50),
                    where=where_filter
                )
                
                # Convert to SearchResult objects
                for i in range(len(results['documents'][0])):
                    distance = results['distances'][0][i]
                    relevance = 1 - distance  # Convert distance to relevance
                    
                    all_results.append(SearchResult(
                        document=results['documents'][0][i],
                        metadata=results['metadatas'][0][i],
                        distance=distance,
                        relevance=relevance
                    ))
                    
            except Exception as e:
                print(f"Error searching {collection_name}: {e}")
        
        # Sort by relevance and return top_k
        all_results.sort(key=lambda x: x.relevance, reverse=True)
        return all_results[:top_k]

    def answer(self,
               query: str,
               collections: Optional[List[str]] = None,
               filters: Optional[Dict] = None,
               top_k: int = 10,
               max_source_chars: int = 600) -> Dict[str, Any]:
        """
        Search the legal corpus and synthesise a concise RAG answer with citations.
        Retrieves sources in a balanced way so legislation and case law both appear.
        """
        # Use balanced per-collection retrieval so one collection cannot drown the others.
        if collections is None:
            collections = list(self.collections.keys())

        per_collection_top = max(3, top_k // 2)
        all_results: List[SearchResult] = []
        seen_docs: set[str] = set()

        for coll_name in collections:
            if coll_name not in self.collections:
                continue
            try:
                coll_results = self.search(
                    query=query,
                    collections=[coll_name],
                    filters=filters,
                    top_k=per_collection_top,
                )
                for r in coll_results:
                    key = (r.document or "").strip()[:200]
                    if key not in seen_docs:
                        seen_docs.add(key)
                        all_results.append(r)
            except Exception as e:
                print(f"[RAG_ANSWER] error searching {coll_name}: {e}")

        # Statute/section boost: if the question names an Act and a section,
        # run a targeted search against nz_legislation and push any hits to the top.
        if self._looks_like_statute_query(query) and "nz_legislation" in self.collections:
            try:
                leg_results = self.search(
                    query=query,
                    collections=["nz_legislation"],
                    filters=filters,
                    top_k=5,
                )
                # Insert legislation results at the front so they dominate the answer.
                boosted = []
                seen_boost = set()
                for r in leg_results:
                    key = (r.document or "").strip()[:200]
                    if key not in seen_boost:
                        seen_boost.add(key)
                        boosted.append(r)
                # Append remaining results without duplication.
                for r in all_results:
                    key = (r.document or "").strip()[:200]
                    if key not in seen_boost:
                        boosted.append(r)
                all_results = boosted
            except Exception as e:
                print(f"[RAG_ANSWER] legislation boost failed: {e}")

        # Final rank by relevance and truncate to top_k.
        all_results.sort(key=lambda x: x.relevance, reverse=True)
        results = all_results[:top_k]

        if not results:
            return {
                "answer": "No relevant sources were found for this question.",
                "sources": [],
                "query": query,
            }

        # Build a numbered context block from the retrieved sources.
        context_parts = []
        source_summaries = []
        for i, r in enumerate(results, 1):
            doc = (r.document or "").strip().replace("\n", " ")
            snippet = doc[:max_source_chars]
            meta = r.metadata or {}
            title = meta.get("title") or meta.get("source") or meta.get("category") or "Source"
            context_parts.append(f"[{i}] {title}: {snippet}")
            source_summaries.append({
                "index": i,
                "document": r.document[:500],
                "metadata": r.metadata,
                "relevance": round(r.relevance, 4),
            })

        context = "\n\n".join(context_parts)

        prompt = f"""You are a senior New Zealand criminal-defence research assistant.
Answer the user's legal question using ONLY the retrieved sources below.

INSTRUCTIONS:
- Be concise, accurate, and practical.
- Cite sources inline using the numbered labels [1], [2], etc.
- Do NOT cite any source that is not listed below.
- If the sources do not contain enough information to answer, say so clearly.
- Do not invent cases, statutes, or facts.

RETRIEVED SOURCES:
{context}

USER QUESTION:
{query}

ANSWER:"""

        try:
            if self.llm is None:
                answer_text = "[LLM not available — returning sources only]"
            else:
                answer_text = self.llm.invoke(prompt)
        except Exception as e:
            answer_text = f"[Error generating answer: {e}]"

        return {
            "query": query,
            "answer": answer_text,
            "sources": source_summaries,
        }

    @staticmethod
    def _looks_like_statute_query(query: str) -> bool:
        """Detect queries that ask about a specific statute section."""
        q = (query or "").lower()
        has_act = "act" in q
        has_section = bool(re.search(r"\b(?:s|section|ss)\s*\d+", q))
        return has_act and has_section

    def _build_where_filter(self, filters: Optional[Dict], collection_name: str) -> Optional[Dict]:
        """Build ChromaDB where filter from user filters"""
        if not filters:
            return None
        
        where = {}
        
        if 'year_min' in filters and 'year_max' in filters:
            where['year'] = {
                "$gte": filters['year_min'],
                "$lte": filters['year_max']
            }
        
        if 'court' in filters:
            where['court'] = filters['court']
        
        if 'act' in filters:
            where['act'] = filters['act']
        
        return where if where else None
    
    def legal_analysis(self,
                       query: str,
                       context_results: Optional[List[SearchResult]] = None,
                       analysis_type: str = "general",
                       collections: Optional[List[str]] = None,
                       deep_analysis: bool = False,
                       filters: Optional[Dict[str, Any]] = None,
                       raw_disclosure: Optional[str] = None) -> LegalAnalysis:
        """
        Full multi-agent legal analysis pipeline with per-agent timing.

        Orchestration:
        1. Case Intake Agent      → classifies intent, refines query, plans retrieval.
        2. Retrieval              → temp docs (full) + permanent collections (semantic).
        3. Defence Analyst        → generates adversarial legal analysis.
        4. Parallel agents        → Citation Auditor + Defence Strategist (ThreadPoolExecutor).
        5. Optional re-search     → if auditor finds missing citations (one pass).
        6. Synthesis Agent        → assembles final formatted response.
        7. Post-processing        → confidence scoring, legacy citation guard fallback.

        Args:
            query: Legal question or scenario
            context_results: Pre-fetched search results (optional, skips intake+retrieval)
            analysis_type: User-selected type (overridden by intake agent if ambiguous)
            collections: Collections to search
        """
        t_start = time.perf_counter()
        timings: Dict[str, float] = {}

        # ------------------------------------------------------------------
        # STEP 1 — Intake Agent
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        intake: Optional[IntakeResult] = None
        if context_results is None and self.llm:
            try:
                intake = self.intake_agent.intake(
                    raw_query=query,
                    available_collections=collections or list(self.collections.keys())
                )
            except Exception as e:
                print(f"[IntakeAgent warning] {e}")
        timings["intake"] = round(time.perf_counter() - t0, 2)

        effective_type = intake.detected_analysis_type if intake else analysis_type
        refined_query = intake.refined_query if intake else query
        search_queries = intake.search_queries if intake else [query]
        target_collections = intake.suggested_collections if intake else (collections or list(self.collections.keys()))

        # Initialise observability trace
        agent_trace: Dict[str, Any] = {
            "intake": {
                "raw_query": query,
                "detected_analysis_type": effective_type,
                "refined_query": refined_query,
                "search_queries": search_queries,
                "suggested_collections": target_collections,
                "key_entities": intake.key_entities if intake else {},
                "intake_summary": intake.intake_summary if intake else "",
                "intake_confidence": intake.confidence if intake else 0.0,
            },
            "retrieval": {
                "collections_searched": target_collections,
                "temp_collections": [c for c in target_collections if c.startswith('temp_session_')],
                "permanent_collections": [c for c in target_collections if not c.startswith('temp_session_')],
            },
        }

        # ------------------------------------------------------------------
        # STEP 2 — Retrieval
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        if context_results is None:
            context_results = self._retrieve_context(target_collections, search_queries, refined_query, collections, filters=filters)
        timings["retrieval"] = round(time.perf_counter() - t0, 2)

        # ------------------------------------------------------------------
        # STEP 3 — Defence Analysis Agent
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        context_text = self._build_analysis_context(context_results, effective_type)

        # Extract raw uploaded disclosure text and parse the authoritative primary charge.
        # This prevents the model from fixating on background offences (e.g., burglary
        # in warrants) when the actual charge is something else (e.g., GBL possession).
        # If the caller already provided a raw disclosure (e.g., from uploaded_context),
        # use that instead of reconstructing from search results.
        if raw_disclosure:
            raw_disclosure_text = raw_disclosure
            print(f"[RAG_ENGINE] using caller-provided raw_disclosure length={len(raw_disclosure_text)}")
        else:
            raw_disclosure_text = self._extract_raw_disclosure_from_results(context_results)
        primary_charge = None
        witnesses = None
        if raw_disclosure_text:
            try:
                parser = DisclosureParser()
                parsed = parser.parse(raw_disclosure_text)
                primary_charge = parsed.primary_charge
                witnesses = parsed.witnesses
                # Strip out background narrative (burglary/trailer) so the model
                # focuses only on the actual charge.
                raw_disclosure_text = parser.extract_charge_focused_text(
                    raw_disclosure_text, primary_charge, max_chars=18_000
                )
                print(f"[RAG_ENGINE] primary_charge={primary_charge}, focused_length={len(raw_disclosure_text)}, "
                      f"contains_gbl={'gbl' in raw_disclosure_text.lower()}, contains_burglary={'burglary' in raw_disclosure_text.lower()}")
            except Exception as e:
                print(f"[Parser warning in legal_analysis] {e}")

        # If we have a charge-focused raw disclosure, remove uploaded-document
        # chunks from the retrieved context so they cannot override the facts.
        # The legal sources (legislation, case law, Police Manual) remain for
        # principles only.
        if raw_disclosure_text:
            context_text = self._filter_uploaded_chunks_from_context(context_text)

        if self.llm:
            analysis_response = self.defence_analyst.analyze(
                refined_query, context_text, effective_type,
                primary_charge=primary_charge,
                raw_disclosure=raw_disclosure_text,
                witnesses=witnesses
            )
        else:
            analysis_response = "[LLM not configured]"
        timings["defence_analyst"] = round(time.perf_counter() - t0, 2)

        agent_trace["defence_analyst"] = {
            "analysis_type": effective_type,
            "context_length_chars": len(context_text),
            "context_chunks": len(context_results),
            "response_length_chars": len(analysis_response),
            "response_preview": analysis_response[:300] + "..." if len(analysis_response) > 300 else analysis_response,
        }

        # ------------------------------------------------------------------
        # STEP 4 — Parallel: Citation Auditor + Defence Strategist (DEEP only)
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        audit: Optional[AuditResult] = None
        strategy: Optional[StrategyResult] = None

        if deep_analysis and self.llm and analysis_response and not analysis_response.startswith("["):
            with ThreadPoolExecutor(max_workers=2) as executor:
                future_audit = executor.submit(
                    self.citation_auditor.audit,
                    analysis_response,
                    context_results,
                    refined_query
                )
                future_strategy = executor.submit(
                    self.defence_strategist.strategize,
                    analysis_response,
                    intake,
                    context_results
                )

                for future in as_completed([future_audit, future_strategy]):
                    try:
                        result = future.result()
                        if isinstance(result, AuditResult):
                            audit = result
                        elif isinstance(result, StrategyResult):
                            strategy = result
                    except Exception as e:
                        print(f"[Parallel agent warning] {e}")
        timings["parallel_auditor_strategist"] = round(time.perf_counter() - t0, 2)

        agent_trace["citation_auditor"] = {
            "verified_citations": audit.verified_citations if audit else [],
            "unverified_citations": audit.unverified_citations if audit else [],
            "hallucination_risk": audit.hallucination_risk if audit else 0.0,
            "needs_re_search": audit.needs_re_search if audit else False,
            "re_search_queries": audit.re_search_queries if audit else [],
            "audit_report": audit.audit_report if audit else "",
        } if audit else {"status": "skipped or failed"}

        agent_trace["defence_strategist"] = {
            "procedural_motions": strategy.procedural_motions if strategy else [],
            "cross_examination_angles": strategy.cross_examination_angles if strategy else [],
            "plea_considerations": strategy.plea_considerations if strategy else "",
            "tactical_priorities": strategy.tactical_priorities if strategy else [],
            "risk_flags": strategy.risk_flags if strategy else [],
            "executive_summary": strategy.executive_summary if strategy else "",
        } if strategy else {"status": "skipped or failed"}

        # ------------------------------------------------------------------
        # STEP 5 — Optional one-pass re-search for missing citations (DEEP only)
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        if deep_analysis and audit and audit.needs_re_search and audit.re_search_queries:
            try:
                extra_results = []
                seen = {r.document[:200] for r in context_results}
                for sq in audit.re_search_queries[:2]:
                    for r in self.search(sq, collections=target_collections, top_k=3):
                        h = r.document[:200]
                        if h not in seen:
                            seen.add(h)
                            extra_results.append(r)
                if extra_results:
                    context_results.extend(extra_results)
                    # Re-run analysis with expanded context
                    context_text = self._build_analysis_context(context_results, effective_type)
                    # Re-extract raw disclosure in case new temp chunks were added
                    raw_disclosure_text = self._extract_raw_disclosure_from_results(context_results)
                    if raw_disclosure_text and primary_charge:
                        try:
                            raw_disclosure_text = DisclosureParser().extract_charge_focused_text(
                                raw_disclosure_text, primary_charge, max_chars=18_000
                            )
                        except Exception:
                            pass
                    analysis_response = self.defence_analyst.analyze(
                        refined_query, context_text, effective_type,
                        primary_charge=primary_charge,
                        raw_disclosure=raw_disclosure_text,
                        witnesses=witnesses
                    )
                    # Re-audit
                    audit = self.citation_auditor.audit(analysis_response, context_results, refined_query)
                    agent_trace["re_search"] = {
                        "triggered": True,
                        "queries_used": audit.re_search_queries[:2] if audit else [],
                        "extra_chunks_found": len(extra_results),
                    }
            except Exception as e:
                print(f"[Re-search warning] {e}")
                agent_trace["re_search"] = {"triggered": False, "error": str(e)}
        else:
            agent_trace["re_search"] = {"triggered": False}
        timings["re_search"] = round(time.perf_counter() - t0, 2)

        # ------------------------------------------------------------------
        # STEP 6 — Synthesis Agent (DEEP only, else minimal assembly)
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        if deep_analysis:
            synthesis = self.synthesis_agent.synthesize(
            analysis_text=analysis_response,
            audit=audit,
            strategy=strategy,
            intake=intake,
            confidence=0.0,  # placeholder, calculated below
            sources=context_results
        )
            timings["synthesis"] = round(time.perf_counter() - t0, 2)
        else:
            # Fast mode: minimal assembly, skip auditor/strategist/synthesis
            synthesis = SynthesisResult(
                formatted_answer=analysis_response,
                executive_summary="",
                confidence_breakdown="",
                citation_warnings="",
                strategic_appendix="",
                metadata={}
            )
            timings["synthesis"] = 0.0

        # ------------------------------------------------------------------
        # STEP 7 — Confidence scoring & legacy citation guard fallback
        # ------------------------------------------------------------------
        t0 = time.perf_counter()
        citations = self._extract_citations(analysis_response, context_results)
        source_texts = [r.document for r in context_results[:10]]
        _, verify_score, warning = self.citation_guard.verify(analysis_response, source_texts)

        if warning and warning not in analysis_response:
            analysis_response += warning

        confidence = self._calculate_confidence(context_results, analysis_response, verify_score)

        # Dampen confidence if intake was uncertain or auditor found issues
        if intake and intake.confidence < 0.6:
            confidence = round(confidence * 0.85, 2)
        if audit and audit.hallucination_risk > 0.3:
            confidence = round(confidence * (1 - audit.hallucination_risk * 0.5), 2)

        # Update synthesis with final confidence
        synthesis.confidence_breakdown = self.synthesis_agent._build_confidence_breakdown(
            confidence, intake, audit
        )
        timings["post_processing"] = round(time.perf_counter() - t0, 2)

        agent_trace["synthesis"] = {
            "executive_summary": synthesis.executive_summary,
            "strategic_appendix_length": len(synthesis.strategic_appendix),
            "citation_warnings_length": len(synthesis.citation_warnings),
            "confidence_breakdown": synthesis.confidence_breakdown,
        }
        timings["total"] = round(time.perf_counter() - t_start, 2)
        agent_trace["timings"] = timings
        agent_trace["pipeline"] = {
            "total_chunks_retrieved": len(context_results),
            "final_confidence": confidence,
            "agents_used": ["intake", "retrieval", "defence_analyst"] + (["citation_auditor", "defence_strategist", "synthesis"] if deep_analysis else []), "deep_analysis": deep_analysis,
        }

        return LegalAnalysis(
            query=refined_query,
            answer=synthesis.formatted_answer,
            citations=citations,
            sources=context_results[:5],
            confidence=confidence,
            analysis_type=effective_type,
            executive_summary=synthesis.executive_summary,
            audit_report=getattr(audit, "audit_report", "") if audit else "",
            strategic_notes=synthesis.strategic_appendix,
            confidence_breakdown=synthesis.confidence_breakdown,
            metadata=getattr(synthesis, "metadata", {}),
            agent_trace=agent_trace
        )

    def deep_disclosure_analysis(
            self,
            focus_area: str,
            disclosure_text: str,
            collections: Optional[List[str]] = None,
            previous_analysis: Optional[str] = None) -> LegalAnalysis:
        """
        Focused deep-dive analysis on a specific aspect of a disclosure.

        Args:
            focus_area: The issue the user wants explored in depth, e.g.
                        "search warrant validity", "identification evidence",
                        "disclosure gaps", "voluntariness of admissions".
            disclosure_text: The full police disclosure text.
            collections: Collections to search for legal principles.
            previous_analysis: Optional text from the prior full analysis to
                               avoid repeating ground already covered.
        """
        analysis_type = "general"
        focus_lower = (focus_area or "").lower()
        if any(k in focus_lower for k in ("search", "warrant", "s 21", "ss 21", "bora")):
            analysis_type = "search_warrant"
        elif any(k in focus_lower for k in ("charge", "element", "offence", "offense")):
            analysis_type = "charge_review"
        elif any(k in focus_lower for k in ("disclosure", "brady", "late disclosure")):
            analysis_type = "disclosure_review"

        query = f"Deep analysis: {focus_area}"
        return self.legal_analysis(
            query=query,
            analysis_type=analysis_type,
            collections=collections,
            deep_analysis=True,
            raw_disclosure=disclosure_text,
        )

    def _retrieve_context(self, target_collections: List[str], search_queries: List[str],
                          refined_query: str, fallback_collections: Optional[List[str]],
                          filters: Optional[Dict[str, Any]] = None) -> List[SearchResult]:
        """Shared retrieval logic for the pipeline."""
        context_results: List[SearchResult] = []

        temp_collections = [c for c in target_collections if c.startswith('temp_session_')]
        permanent_collections = [c for c in target_collections if not c.startswith('temp_session_')]

        # Retrieve ALL uploaded document chunks in reading order
        for temp_coll_name in temp_collections:
            if temp_coll_name in self.collections:
                coll = self.collections[temp_coll_name]
                all_data = coll.get(include=['documents', 'metadatas'])
                temp_results = []
                for i in range(len(all_data['ids'])):
                    temp_results.append(SearchResult(
                        document=all_data['documents'][i],
                        metadata=all_data['metadatas'][i],
                        distance=0.0,
                        relevance=1.0
                    ))
                temp_results.sort(key=lambda x: x.metadata.get('chunk_index', 0))
                context_results.extend(temp_results[:35])

        # Semantic search on permanent collections using optimised queries
        if permanent_collections:
            seen_docs = set()
            for sq in search_queries[:3]:
                legal_results = self.search(sq, collections=permanent_collections, top_k=5)
                for r in legal_results:
                    doc_hash = r.document[:200]
                    if doc_hash not in seen_docs:
                        seen_docs.add(doc_hash)
                        context_results.append(r)

        # Fallback
        if not context_results:
            context_results = self.search(refined_query, collections=fallback_collections, filters=filters, top_k=10)

        return context_results
    
    def _extract_raw_disclosure_from_results(self, results: List[SearchResult]) -> str:
        """Reconstruct the raw uploaded disclosure text from uploaded document chunks.

        Uploaded documents may live in temp_session_* collections, user_uploads, or
        any user-named collection (e.g., scanned_document.txt). We treat anything that
        is not a known permanent legal source as an uploaded disclosure.
        """
        legal_collections = {
            "nz_legislation", "nz_case_law", "nzlii_criminal_cases",
            "nz_police_manual", "legal_research",
        }
        uploaded_results = []
        for r in results:
            category = r.metadata.get("category", "")
            source = r.metadata.get("source", r.metadata.get("filename", ""))
            is_upload = (
                category.startswith("temp_session_")
                or category == "user_uploads"
                or (category and category not in legal_collections)
                or (source and source.lower().endswith((".txt", ".pdf", ".docx", ".doc")))
            )
            if is_upload:
                uploaded_results.append(r)
        if not uploaded_results:
            return ""
        # Sort by chunk_index if available to preserve reading order
        uploaded_results.sort(key=lambda r: r.metadata.get("chunk_index", 0))
        return "\n\n".join(r.document for r in uploaded_results)

    def _filter_uploaded_chunks_from_context(self, context_text: str) -> str:
        """Remove uploaded-document chunks from the retrieved context string.

        Once we have a charge-focused raw disclosure, the uploaded chunks are
        redundant and may contain distracting background narrative. Legal sources
        (legislation, case law, Police Manual) are retained.
        """
        parts = []
        for part in context_text.split("\n\n---\n\n"):
            stripped = part.strip()
            if stripped.startswith("[UPLOADED DOCUMENT"):
                continue
            if stripped.startswith("[TEMP_SESSION"):
                continue
            parts.append(part)
        return "\n\n---\n\n".join(parts) if parts else context_text

    def _build_analysis_context(self, results: List[SearchResult], analysis_type: str) -> str:
        """Build context string from search results"""
        context_parts = []
        
        # Group by category
        uploaded_docs = []
        legislation = []
        case_law = []
        other = []
        
        for result in results:
            category = result.metadata.get('category', 'unknown')
            source = result.metadata.get('source', result.metadata.get('title', 'Unknown'))
            
            # Uploaded/temp documents get larger truncation and priority
            if category.startswith('temp_session_') or category == 'user_uploads':
                page_ref = result.metadata.get("page_number")
                page_label = f" (page {page_ref})" if page_ref else ""
                chunk = f"[UPLOADED DOCUMENT - {source}{page_label}]\n{result.document[:1500]}"
                uploaded_docs.append(chunk)
            elif category == 'legislation':
                chunk = f"[{category.upper()} - {source} - Relevance: {result.relevance:.1%}]\n{result.document[:800]}"
                legislation.append(chunk)
            elif category == 'case_law':
                chunk = f"[{category.upper()} - {source} - Relevance: {result.relevance:.1%}]\n{result.document[:800]}"
                case_law.append(chunk)
            else:
                chunk = f"[{category.upper()} - {source} - Relevance: {result.relevance:.1%}]\n{result.document[:800]}"
                other.append(chunk)
        
        # Uploaded docs go FIRST so the model reads them before legislation
        context_parts = uploaded_docs + legislation + case_law + other
        
        return "\n\n---\n\n".join(context_parts)
    
    def _build_analysis_prompt(self, query: str, context: str, analysis_type: str) -> str:
        """Build a defence-focused legal brief prompt."""

        type_focus = {
            "charge_review": "The primary focus is a charge review: break the charge into elements, assess the Crown evidence for each, and identify defence strategies.",
            "search_warrant": "The primary focus is search authority validity: identify breaches of the Search and Surveillance Act 2012 and s 21 NZBORA, and remedies available.",
            "charge_extraction": "The primary focus is extracting all charges and accused persons from the documents.",
            "disclosure_review": "The primary focus is disclosure adequacy: identify missing evidence, late disclosure, and Brady material.",
        }.get(analysis_type, "Provide a comprehensive defence assessment of the legal issue.")

        return f"""You are a senior New Zealand Defence Counsel acting EXCLUSIVELY for the accused. Your sole duty is to ATTACK the prosecution case and secure the best outcome for your client.

ABSOLUTE RULES:
1. Base your answer ONLY on the sources provided below.
2. Frame every observation as: "How does this help the accused?"
3. DO NOT give advice to the prosecution or police.
4. DO NOT assess whether the prosecution case is "strong". Find why it is WEAK, unreliable, or unlawful.
5. Analyse uploaded factual documents for defence advantages: inconsistencies, missing evidence, contradictions, disclosure failures, unreliable witnesses, illegal searches, and procedural breaches.
6. Police Manual deviations are defence wins — exclusion arguments, credibility attacks, or abuse of process.
7. You may ONLY cite a statute, section, regulation, or case if it appears EXPLICITLY in the sources above. If you are unsure, say "[not verified in retrieved sources]".
8. NEVER invent a case name, section number, statute title, or legal authority.
9. For every legal claim, attach a source reference from the retrieved documents (e.g., "[NZ Legislation — Crimes Act 1961, s 231]").

QUERY: {query}

FOCUS: {type_focus}

RELEVANT LEGAL SOURCES AND DOCUMENTS:
{context}

PRODUCE A STRUCTURED LEGAL BRIEF USING ONLY THESE HEADINGS. DO NOT ADD EXTRA TOP-LEVEL HEADINGS.

# EXECUTIVE SUMMARY
2-5 bullet points. State the charge/issue, the most important prosecution weakness, and the headline defence strategy.

# CHARGE AND LEGISLATIVE FRAMEWORK
For each charge or legal issue:
- Offence name and statute section
- Maximum penalty
- Elements the prosecution must prove

# EVIDENCE ANALYSIS
## Prosecution Evidence Strengths
List the evidence that helps the Crown, with brief weight comments.

## Prosecution Evidence Weaknesses
List inconsistencies, gaps, missing evidence, and alternative explanations. Be thorough.

## Key Factual Disputes
Identify genuinely disputed facts and why they matter.

# ELEMENTS OF THE OFFENCE
For each element of each charge:
- Element
- Prosecution evidence
- Defence response / weakness
- Assessment: PROVEN / UNPROVEN / UNCLEAR on the beyond-reasonable-doubt standard

# DEFENCE STRATEGIES
Provide 4-6 distinct defence strategies labelled A, B, C, etc. For each:
- Strategy name
- Legal basis
- Factual foundation
- How to raise it
- Strength rating: STRONG / MODERATE / WEAK

# PRE-TRIAL INSTRUCTIONS FOR LAWYER
Numbered, concrete instructions the accused can give their lawyer.

# EVIDENTIARY ISSUES TO RAISE
Specific objections, disclosure requests, or pre-trial applications with legal basis.

# CONCLUSION AND RISK ASSESSMENT
- Overall case strength assessment
- Acquittal/success prospects
- Sentencing or custody risk if convicted
- Recommended next step

# DISCLAIMER
AI-generated analysis, not legal advice. Consult a qualified New Zealand lawyer.

LEGAL BRIEF:"""
    
    def _extract_citations(self, text: str, results: List[SearchResult]) -> List[str]:
        """Extract legal citations from response"""
        citations = []
        
        # Pattern for NZ case citations
        case_patterns = [
            r'R\s+v\s+[A-Z][a-zA-Z\s]+\[[0-9]{4}\][^\.,;\n]+',
            r'\[[0-9]{4}\]\s+\d+\s+NZLR\s+\d+',
            r'\[[0-9]{4}\]\s+NZSC\s+\d+',
            r'\[[0-9]{4}\]\s+NZCA\s+\d+',
            r'\[[0-9]{4}\]\s+NZHC\s+\d+',
            r'\([0-9]{4}\)\s+\d+\s+CRNZ\s+\d+',
        ]
        
        for pattern in case_patterns:
            matches = re.findall(pattern, text)
            citations.extend(matches)
        
        # Pattern for legislation
        leg_patterns = [
            r'(?:Crimes Act|Misuse of Drugs Act|Evidence Act|Search and Surveillance Act|Criminal Procedure Act|Bill of Rights Act)\s+[0-9]{4}',
            r's(?:ection)?\s*\d+[A-Z]?\s+(?:of\s+)?(?:the\s+)?(?:Crimes|Misuse of Drugs|Evidence|Search and Surveillance|Criminal Procedure|Bill of Rights)',
        ]
        
        for pattern in leg_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            citations.extend(matches)
        
        # Deduplicate while preserving order
        seen = set()
        unique_citations = []
        for c in citations:
            c_clean = c.strip()
            if c_clean.lower() not in seen:
                seen.add(c_clean.lower())
                unique_citations.append(c_clean)
        
        return unique_citations[:15]  # Limit to top 15
    
    def _calculate_confidence(self, results: List[SearchResult], response: str, citation_verify_score: float = 0.5) -> float:
        """Calculate confidence score for the analysis"""
        if not results:
            return 0.0
        
        # Factors:
        # 1. Average relevance of sources (0.0 - 0.5 max)
        avg_relevance = sum(r.relevance for r in results[:5]) / min(5, len(results))
        relevance_weight = avg_relevance * 0.5
        
        # 2. Citation verification score (0.0 - 0.3 max)
        verify_weight = citation_verify_score * 0.3
        
        # 3. Presence of citations (0.0 - 0.1 max)
        citation_bonus = 0.1 if '[' in response and ']' in response else 0
        
        # 4. Diversity of sources (0.0 - 0.1 max)
        categories = set(r.metadata.get('category', '') for r in results[:5])
        diversity_bonus = min(0.1, len(categories) * 0.05)
        
        confidence = min(1.0, relevance_weight + verify_weight + citation_bonus + diversity_bonus)
        return round(confidence, 2)
    
    def find_similar_cases(self, 
                           facts: str,
                           legal_issue: Optional[str] = None,
                           top_k: int = 5) -> List[SearchResult]:
        """
        Find cases with similar fact patterns or legal issues
        """
        query = facts
        if legal_issue:
            query = f"{facts}\n\nLegal issue: {legal_issue}"
        
        results = self.search(
            query=query,
            collections=["nzlii_criminal_cases"],
            top_k=top_k
        )
        
        return results
    
    def check_elements(self, 
                       offense: str,
                       facts: str,
                       statute: Optional[str] = None,
                       collections: Optional[List[str]] = None) -> Dict:
        """
        Check if legal elements are satisfied by given facts
        """
        # Search for offense definition
        search_query = f"{offense} elements"
        if statute:
            search_query += f" {statute}"
        
        results = self.search(search_query, collections=collections, top_k=10)
        
        # Build analysis prompt
        context = self._build_analysis_context(results, "charge_review")
        
        prompt = f"""You are analyzing whether the elements of an offense are satisfied.

OFFENSE: {offense}
STATUTE: {statute or "Not specified"}

FACTS:
{facts}

{context}

Analyze whether each element of the offense is satisfied by the facts provided.
For each element, indicate:
1. Whether it is proven, unproven, or unclear
2. What evidence would be needed to prove it
3. Any potential weaknesses or defenses

Format your response as JSON-like structure with clear headings.
"""
        
        if self.llm:
            response = self.llm.invoke(prompt)
        else:
            response = "[LLM not configured]"
        
        # Parse elements from response
        elements = self._parse_elements_from_response(response)
        
        return {
            "offense": offense,
            "elements": elements,
            "analysis": response,
            "sources": results[:5]
        }
    
    def _parse_elements_from_response(self, response: str) -> List[Dict]:
        """Parse structured elements from LLM response"""
        elements = []
        
        # Look for numbered or bulleted elements
        element_pattern = r'(?:^|\n)\s*(?:\d+\.?|\•|\-|\*)\s*([^\n:]+)(?::|\n)([^\n]+)'
        matches = re.findall(element_pattern, response)
        
        for element, status in matches:
            elements.append({
                "element": element.strip(),
                "status": status.strip(),
                "proven": "proven" in status.lower() or "satisfied" in status.lower(),
                "unclear": "unclear" in status.lower() or "unknown" in status.lower()
            })
        
        return elements
    
    def ingest_document(self, 
                        file_path: str,
                        collection: str = "confidential",
                        metadata: Optional[Dict] = None) -> str:
        """
        Ingest a new document into the database
        """
        if collection not in self.collections:
            try:
                self.collections[collection] = self.client.get_collection(collection)
            except Exception:
                self.collections[collection] = self.client.create_collection(
                    name=collection,
                    metadata={"description": f"Collection for {collection}"}
                )
        
        # Read document
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into chunks
        chunks = self.text_splitter.split_text(content)
        
        # Generate embeddings in batch (much faster than one-by-one)
        chunk_embeddings = self.embeddings.embed_documents(chunks) if chunks else []
        
        # Add to collection
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
            chunk_id = f"{Path(file_path).stem}_chunk_{i}"
            
            chunk_metadata = {
                "source": Path(file_path).name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "category": collection,
                **(metadata or {})
            }
            
            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append(chunk_metadata)
        
        # Add to collection
        self.collections[collection].add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        
        return f"Ingested {len(chunks)} chunks from {file_path}"
    
    def ingest_text(self,
                    documents: List[Dict[str, Any]],
                    collection: str = "user_uploads",
                    metadata: Optional[Dict] = None) -> str:
        """
        Ingest text documents into a collection.
        Supports optional page-aware metadata via document keys:
        - name
        - content
        - file_type
        - page_texts: [{"page_number": int, "text": str}]
        """
        if collection not in self.collections:
            try:
                self.collections[collection] = self.client.get_collection(collection)
            except Exception:
                self.collections[collection] = self.client.create_collection(
                    name=collection,
                    metadata={"description": f"Collection for {collection}"}
                )

        total_chunks = 0

        for doc in documents:
            name = doc.get("name", "unknown")
            content = doc.get("content", "")
            file_type = doc.get("file_type")
            page_texts = doc.get("page_texts") or []
            doc_metadata = dict(doc.get("metadata") or {})
            source_name = doc_metadata.get("source") or doc_metadata.get("title") or doc_metadata.get("filename") or name
            title_name = doc_metadata.get("title") or doc_metadata.get("filename") or source_name
            filename = doc_metadata.get("filename") or name
            document_id = hashlib.md5(f"{collection}:{name}:{len(content)}".encode("utf-8")).hexdigest()[:16]

            ids = []
            embeddings = []
            documents_out = []
            metadatas = []

            if page_texts:
                chunk_counter = 0
                for page in page_texts:
                    page_number = page.get("page_number")
                    page_content = (page.get("text") or "").strip()
                    if not page_content:
                        continue
                    chunks = self.text_splitter.split_text(page_content)
                    chunk_embeddings = self.embeddings.embed_documents(chunks) if chunks else []
                    for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                        chunk_id = f"{document_id}_p{page_number}_c{i}"
                        chunk_metadata = dict(doc_metadata)
                        chunk_metadata.update({
                            "source": source_name,
                            "title": title_name,
                            "filename": filename,
                            "document_id": document_id,
                            "page_number": page_number,
                            "page": page_number,
                            "pagenumber": page_number,
                            "chunk_index": chunk_counter,
                            "file_type": file_type or "",
                            "category": collection,
                        })
                        for k, v in (metadata or {}).items():
                            chunk_metadata.setdefault(k, v)
                        ids.append(chunk_id)
                        embeddings.append(embedding)
                        documents_out.append(chunk)
                        metadatas.append(chunk_metadata)
                        chunk_counter += 1
            else:
                chunks = self.text_splitter.split_text(content)
                chunk_embeddings = self.embeddings.embed_documents(chunks) if chunks else []
                for i, (chunk, embedding) in enumerate(zip(chunks, chunk_embeddings)):
                    chunk_id = f"{document_id}_c{i}"
                    chunk_metadata = dict(doc_metadata)
                    chunk_metadata.update({
                        "source": source_name,
                        "title": title_name,
                        "filename": filename,
                        "document_id": document_id,
                        "chunk_index": i,
                        "file_type": file_type or "",
                        "category": collection,
                    })
                    for k, v in (metadata or {}).items():
                        chunk_metadata.setdefault(k, v)
                    ids.append(chunk_id)
                    embeddings.append(embedding)
                    documents_out.append(chunk)
                    metadatas.append(chunk_metadata)

            if ids:
                self.collections[collection].add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents_out,
                    metadatas=metadatas
                )
                total_chunks += len(ids)

        return f"Ingested {total_chunks} chunks into {collection}"


    def get_database_stats(self) -> Dict:
        """Get statistics about the database — counts unique source documents, not chunks"""
        stats = {
            "collections": {},
            "total_documents": 0,
            "total_chunks": 0
        }
        
        for name, collection in self.collections.items():
            chunk_count = collection.count()
            unique_docs = 0
            if chunk_count > 0:
                try:
                    res = collection.get(include=["metadatas"])
                    sources = set()
                    for m in res["metadatas"]:
                        src = m.get("source") or m.get("title") or m.get("filename") or m.get("act_name") or "unknown"
                        sources.add(src)
                    unique_docs = len(sources)
                except Exception:
                    unique_docs = chunk_count  # fallback
            
            stats["collections"][name] = {
                "count": chunk_count,
                "documents": unique_docs,
                "description": self.COLLECTIONS.get(name, "Unknown")
            }
            stats["total_documents"] += unique_docs
            stats["total_chunks"] += chunk_count
        
        return stats

    def list_all_collections(self) -> List[Dict[str, Any]]:
        """Return every collection in ChromaDB, including user-created ones."""
        result = []
        try:
            for coll in self.client.list_collections():
                name = getattr(coll, "name", str(coll))
                count = 0
                try:
                    count = self.client.get_collection(name).count()
                except Exception:
                    pass
                result.append({
                    "name": name,
                    "description": self.COLLECTIONS.get(name, ""),
                    "document_count": count,
                })
        except Exception as e:
            print(f"[list_all_collections] error: {e}")
        return sorted(result, key=lambda x: x["name"])

    def create_collection(self, name: str, description: str = "") -> None:
        """Create a new empty ChromaDB collection."""
        if name in self.collections:
            return
        try:
            self.collections[name] = self.client.create_collection(
                name=name,
                metadata={"description": description or f"Collection for {name}"},
            )
        except Exception:
            self.collections[name] = self.client.get_collection(name)

    def delete_collection(self, name: str) -> None:
        """Delete a ChromaDB collection."""
        self.client.delete_collection(name=name)
        self.collections.pop(name, None)

    def inspect_collection(self, name: str, offset: int = 0, limit: int = 20) -> Dict[str, Any]:
        """Return paginated chunks and metadata for a collection."""
        coll = self.client.get_collection(name)
        total = coll.count()
        data = coll.get(
            include=["documents", "metadatas"],
            offset=max(0, offset),
            limit=max(1, min(limit, 100)),
        )
        items = []
        for i, doc_id in enumerate(data.get("ids", [])):
            meta = data.get("metadatas", [])[i] if i < len(data.get("metadatas", [])) else {}
            items.append({
                "id": doc_id,
                "document": data.get("documents", [])[i] if i < len(data.get("documents", [])) else "",
                "metadata": meta,
            })
        # Unique source documents
        sources = set()
        for m in data.get("metadatas", []):
            src = m.get("source") or m.get("filename") or m.get("title") or "unknown"
            sources.add(src)
        return {
            "name": name,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": items,
            "unique_sources": sorted(sources),
        }


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NZ Legal RAG Engine")
    parser.add_argument("--db", default="/workspace/chroma_db_fresh", help="Database path")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--collections", "-c", nargs="+", 
                       choices=["legislation", "case_law", "police_manual", "legal_research"],
                       help="Collections to search")
    parser.add_argument("--analyze", "-a", action="store_true", help="Perform AI analysis")
    parser.add_argument("--type", "-t", default="general",
                       choices=["general", "charge_review", "search_warrant", "disclosure_review"],
                       help="Analysis type")
    
    args = parser.parse_args()
    
    # Initialize RAG
    rag = NZLegalRAG(db_path=args.db)
    
    # Show stats
    stats = rag.get_database_stats()
    print(f"Database: {stats['total_documents']} documents ({stats['total_chunks']} chunks)")
    for name, info in stats["collections"].items():
        print(f"  - {name}: {info['documents']} docs ({info['count']} chunks)")
    
    print(f"\nQuery: {args.query}\n")
    
    if args.analyze:
        # Perform legal analysis
        print("Performing legal analysis...")
        analysis = rag.legal_analysis(args.query, analysis_type=args.type)
        
        print(f"\n{'='*70}")
        print(f"LEGAL ANALYSIS (Confidence: {analysis.confidence:.0%})")
        print(f"{'='*70}\n")
        print(analysis.answer)
        
        print(f"\n{'='*70}")
        print("CITATIONS")
        print(f"{'='*70}")
        for citation in analysis.citations:
            print(f"  • {citation}")
        
        print(f"\n{'='*70}")
        print("SOURCES")
        print(f"{'='*70}")
        for i, source in enumerate(analysis.sources, 1):
            print(f"\n[{i}] {source.metadata.get('title', 'Unknown')}")
            print(f"    Category: {source.metadata.get('category', 'Unknown')}")
            print(f"    Relevance: {source.relevance:.1%}")
    else:
        # Just search
        results = rag.search(args.query, collections=args.collections)
        
        print(f"Found {len(results)} results:\n")
        for i, result in enumerate(results, 1):
            print(f"[{i}] {result.metadata.get('title', 'Unknown')}")
            print(f"    Category: {result.metadata.get('category', 'Unknown')}")
            print(f"    Relevance: {result.relevance:.1%}")
            print(f"    {result.document[:300]}...\n")


if __name__ == "__main__":
    main()
