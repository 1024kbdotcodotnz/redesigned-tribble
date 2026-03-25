#!/usr/bin/env python3
"""
NZ Legal RAG Engine
Core retrieval and generation engine for legal research
"""

import os
import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

import chromadb
from chromadb.config import Settings
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
        "legal_master": "Legal Master Database (Existing)",
        "legislation": "NZ Legislation (Acts, Regulations)",
        "case_law": "NZ Case Law (NZLII)",
        "police_manual": "Police Manual Chapters",
        "legal_research": "Legal Research Notes",
        "confidential": "Confidential Documents (Local)"
    }
    
    def __init__(self, 
                 db_path: str = "./chroma_db",
                 embedding_model: str = "nomic-embed-text",
                 llm_model: str = "mixtral:latest",
                 use_local_llm: bool = True):
        self.db_path = Path(db_path)
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        
        # Initialize LLM
        if use_local_llm:
            self.llm = Ollama(
                model=llm_model,
                temperature=0.15,
                num_ctx=8192,
                num_predict=2048
            )
        else:
            self.llm = None
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
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
                       analysis_type: str = "general") -> LegalAnalysis:
        """
        Perform AI-powered legal analysis
        
        Args:
            query: Legal question or scenario
            context_results: Pre-fetched search results (optional)
            analysis_type: Type of analysis (general, charge_review, search_warrant, etc.)
        """
        # Search if no context provided
        if context_results is None:
            context_results = self.search(query, top_k=10)
        
        # Build context
        context_text = self._build_analysis_context(context_results, analysis_type)
        
        # Build prompt based on analysis type
        prompt = self._build_analysis_prompt(query, context_text, analysis_type)
        
        # Generate response
        if self.llm:
            response = self.llm.invoke(prompt)
        else:
            response = "[LLM not configured]"
        
        # Extract citations
        citations = self._extract_citations(response, context_results)
        
        # Calculate confidence
        confidence = self._calculate_confidence(context_results, response)
        
        return LegalAnalysis(
            query=query,
            answer=response,
            citations=citations,
            sources=context_results[:5],
            confidence=confidence,
            analysis_type=analysis_type
        )
    
    def _build_analysis_context(self, results: List[SearchResult], analysis_type: str) -> str:
        """Build context string from search results"""
        context_parts = []
        
        # Group by category
        legislation = []
        case_law = []
        other = []
        
        for result in results:
            category = result.metadata.get('category', 'unknown')
            source = result.metadata.get('source', result.metadata.get('title', 'Unknown'))
            
            chunk = f"[{category.upper()} - {source} - Relevance: {result.relevance:.1%}]\n{result.document[:800]}"
            
            if category == 'legislation':
                legislation.append(chunk)
            elif category == 'case_law':
                case_law.append(chunk)
            else:
                other.append(chunk)
        
        # Combine in priority order
        context_parts = legislation + case_law + other
        
        return "\n\n---\n\n".join(context_parts)
    
    def _build_analysis_prompt(self, query: str, context: str, analysis_type: str) -> str:
        """Build analysis prompt based on type"""
        
        base_prompt = f"""You are a senior New Zealand Crown Counsel providing expert legal analysis.

QUERY: {query}

RELEVANT LEGAL SOURCES:
{context}

"""
        
        if analysis_type == "charge_review":
            prompt_addition = """INSTRUCTIONS:
1. Identify the elements of the alleged offense
2. Assess what evidence would be required to prove each element
3. Note any potential defenses or weaknesses
4. Cite applicable legislation sections
5. Reference relevant case law on similar charges
6. Provide a preliminary assessment of the strength of the case

Structure your response with clear headings for each element.
"""
        elif analysis_type == "search_warrant":
            prompt_addition = """INSTRUCTIONS:
1. Assess the validity of the search authority
2. Check compliance with Section 21 NZBORA and Search and Surveillance Act 2012
3. Identify any procedural deficiencies
4. Evaluate the 'reasonable grounds' requirement
5. Note any potential remedies (evidence exclusion, etc.)
6. Cite relevant case law on search warrant validity

Use the Shaheed balancing test framework where applicable.
"""
        elif analysis_type == "disclosure_review":
            prompt_addition = """INSTRUCTIONS:
1. Identify disclosure obligations under Criminal Procedure Act 2011
2. Assess whether all required categories of evidence have been disclosed
3. Note any gaps or deficiencies in disclosure
4. Consider defense strategies based on disclosure issues
5. Reference relevant case law on disclosure obligations
"""
        else:
            prompt_addition = """INSTRUCTIONS:
1. Provide a comprehensive legal analysis of the query
2. Cite specific legislation sections where relevant
3. Reference applicable case law principles
4. Identify elements that must be proven (if criminal matter)
5. Note any procedural considerations or defenses
6. Use clear headings and structure
7. Be precise about legal standards and burdens of proof
"""
        
        return base_prompt + prompt_addition + "\n\nLEGAL ANALYSIS:"
    
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
    
    def _calculate_confidence(self, results: List[SearchResult], response: str) -> float:
        """Calculate confidence score for the analysis"""
        if not results:
            return 0.0
        
        # Factors:
        # 1. Average relevance of sources
        avg_relevance = sum(r.relevance for r in results[:5]) / min(5, len(results))
        
        # 2. Presence of citations
        citation_bonus = 0.1 if '[' in response and ']' in response else 0
        
        # 3. Diversity of sources
        categories = set(r.metadata.get('category', '') for r in results[:5])
        diversity_bonus = len(categories) * 0.05
        
        confidence = min(1.0, avg_relevance + citation_bonus + diversity_bonus)
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
            collections=["case_law"],
            top_k=top_k
        )
        
        return results
    
    def check_elements(self, 
                       offense: str,
                       facts: str,
                       statute: Optional[str] = None) -> Dict:
        """
        Check if legal elements are satisfied by given facts
        """
        # Search for offense definition
        search_query = f"{offense} elements"
        if statute:
            search_query += f" {statute}"
        
        results = self.search(search_query, top_k=10)
        
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
            # Create collection if it doesn't exist
            self.collections[collection] = self.client.create_collection(
                name=collection,
                metadata={"description": f"Collection for {collection}"}
            )
        
        # Read document
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split into chunks
        chunks = self.text_splitter.split_text(content)
        
        # Generate embeddings and add to collection
        ids = []
        embeddings = []
        documents = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{Path(file_path).stem}_chunk_{i}"
            chunk_embedding = self.embeddings.embed_documents([chunk])[0]
            
            chunk_metadata = {
                "source": Path(file_path).name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "category": collection,
                **(metadata or {})
            }
            
            ids.append(chunk_id)
            embeddings.append(chunk_embedding)
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
    
    def get_database_stats(self) -> Dict:
        """Get statistics about the database"""
        stats = {
            "collections": {},
            "total_documents": 0
        }
        
        for name, collection in self.collections.items():
            count = collection.count()
            stats["collections"][name] = {
                "count": count,
                "description": self.COLLECTIONS.get(name, "Unknown")
            }
            stats["total_documents"] += count
        
        return stats


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="NZ Legal RAG Engine")
    parser.add_argument("--db", default="./chroma_db", help="Database path")
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
    print(f"Database: {stats['total_documents']} documents")
    for name, info in stats["collections"].items():
        print(f"  - {name}: {info['count']} documents")
    
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
