#!/usr/bin/env python3
"""
NZ Legal RAG - MCP Server
FastMCP-based Model Context Protocol server for legal research.

Supports stdio, sse, and streamable-http transports.
RunPod deployment ready.
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
from typing import Any
from pathlib import Path
from contextlib import asynccontextmanager

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field

from core.rag_engine import NZLegalRAG, SearchResult, LegalAnalysis

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DB_PATH = os.getenv("CHROMA_DB_PATH", "./chroma_db")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
LLM_MODEL = os.getenv("LLM_MODEL", "mixtral:latest")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")  # stdio | sse | streamable-http
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8080"))
MCP_PATH = os.getenv("MCP_PATH", "/mcp")

# ---------------------------------------------------------------------------
# Lifespan: initialise RAG engine once and share it across requests
# ---------------------------------------------------------------------------
@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """Initialise the NZ Legal RAG engine on startup."""
    print("[NZ Legal MCP] Initialising RAG engine...")
    rag = NZLegalRAG(
        db_path=DB_PATH,
        embedding_model=EMBEDDING_MODEL,
        llm_model=LLM_MODEL,
        use_local_llm=True,
    )
    stats = rag.get_database_stats()
    print(f"[NZ Legal MCP] ✓ Loaded {stats['total_documents']} documents")
    yield {"rag": rag}
    print("[NZ Legal MCP] Shutting down...")


# ---------------------------------------------------------------------------
# FastMCP app
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "nz-legal-rag",
    instructions=(
        "NZ Legal RAG MCP Server – search New Zealand legislation, case law, "
        "and police manuals. Perform legal analysis, find similar cases, and "
        "check offense elements."
    ),
    lifespan=app_lifespan,
)


def _get_rag(ctx: Context) -> NZLegalRAG:
    """Helper to extract the RAG engine from the lifespan context."""
    return ctx.request_context.lifespan_context["rag"]


def _result_to_dict(r: SearchResult) -> dict[str, Any]:
    return {
        "document": r.document[:2000],  # Truncate for MCP payload limits
        "metadata": r.metadata,
        "relevance": round(r.relevance, 4),
    }


def _analysis_to_dict(a: LegalAnalysis) -> dict[str, Any]:
    return {
        "query": a.query,
        "answer": a.answer,
        "citations": a.citations,
        "confidence": round(a.confidence, 4),
        "analysis_type": a.analysis_type,
        "sources": [_result_to_dict(s) for s in a.sources],
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
@mcp.tool()
def search_legal_database(
    query: str = Field(..., description="Search query (min 3 chars)"),
    collections: list[str] | None = Field(
        default=None,
        description=(
            "Collections to search. Defaults to all. "
            "Options: nz_legal_unified, nz_legislation, nzlii_criminal_cases, user_uploads"
        ),
    ),
    top_k: int = Field(default=10, ge=1, le=50, description="Number of results"),
    filters: str | None = Field(
        default=None,
        description='Optional JSON metadata filters, e.g. {"year": {"$gte": 2020}}}',
    ),
    ctx: Context = None,
) -> str:
    """
    Search the New Zealand legal database across legislation, case law,
    and uploaded documents. Returns ranked results with relevance scores.
    """
    if len(query) < 3:
        return "Error: query must be at least 3 characters."

    rag = _get_rag(ctx)
    parsed_filters = None
    if filters:
        try:
            parsed_filters = json.loads(filters)
        except json.JSONDecodeError as e:
            return f"Error: invalid filters JSON – {e}"

    results = rag.search(
        query=query,
        collections=collections,
        filters=parsed_filters,
        top_k=top_k,
    )

    if not results:
        return "No results found."

    lines = [f"Found {len(results)} result(s):\n"]
    for i, r in enumerate(results, 1):
        title = r.metadata.get("title", "Unknown")
        category = r.metadata.get("category", "Unknown")
        lines.append(
            f"[{i}] {title}  (category: {category}, relevance: {r.relevance:.1%})\n"
            f"{r.document[:800]}...\n"
        )
    return "\n".join(lines)


@mcp.tool()
def legal_analysis(
    query: str = Field(..., description="Legal question or scenario (min 10 chars)"),
    analysis_type: str = Field(
        default="general",
        description="Type: general | charge_review | search_warrant | disclosure_review",
    ),
    context: str | None = Field(
        default=None, description="Additional facts or context"
    ),
    collections: list[str] | None = Field(
        default=None, description="Collections to search"
    ),
    ctx: Context = None,
) -> str:
    """
    Perform AI-powered legal analysis on a New Zealand legal question.
    Supports charge review, search-warrant review, disclosure review,
    and general legal analysis.
    """
    if len(query) < 10:
        return "Error: query must be at least 10 characters."

    rag = _get_rag(ctx)
    full_query = query
    if context:
        full_query = f"{query}\n\nContext: {context}"

    analysis = rag.legal_analysis(
        query=full_query,
        analysis_type=analysis_type,
        collections=collections,
    )

    lines = [
        f"Analysis Type: {analysis.analysis_type}",
        f"Confidence: {analysis.confidence:.0%}",
        "",
        analysis.answer,
        "",
        "Citations:",
    ]
    for c in analysis.citations:
        lines.append(f"  • {c}")
    lines.append("")
    lines.append("Sources:")
    for s in analysis.sources:
        title = s.metadata.get("title", "Unknown")
        lines.append(f"  - {title} (relevance {s.relevance:.1%})")

    return "\n".join(lines)


@mcp.tool()
def find_similar_cases(
    facts: str = Field(..., description="Case facts (min 20 chars)"),
    legal_issue: str | None = Field(default=None, description="Specific legal issue"),
    top_k: int = Field(default=5, ge=1, le=20),
    ctx: Context = None,
) -> str:
    """
    Find NZ criminal cases with similar fact patterns or legal issues.
    Searches the nzlii_criminal_cases collection.
    """
    if len(facts) < 20:
        return "Error: facts must be at least 20 characters."

    rag = _get_rag(ctx)
    results = rag.find_similar_cases(
        facts=facts,
        legal_issue=legal_issue,
        top_k=top_k,
    )

    if not results:
        return "No similar cases found."

    lines = [f"Found {len(results)} similar case(s):\n"]
    for i, r in enumerate(results, 1):
        title = r.metadata.get("title", "Unknown")
        citation = r.metadata.get("citation", "")
        court = r.metadata.get("court", "Unknown")
        year = r.metadata.get("year", "")
        lines.append(
            f"[{i}] {title}  {citation}\n"
            f"    Court: {court}  Year: {year}  Relevance: {r.relevance:.1%}\n"
            f"    {r.document[:600]}...\n"
        )
    return "\n".join(lines)


@mcp.tool()
def check_legal_elements(
    offense: str = Field(..., description="Name of the offense"),
    facts: str = Field(..., description="Facts to check against elements"),
    statute: str | None = Field(default=None, description="Relevant statute (optional)"),
    collections: list[str] | None = Field(default=None, description="Collections to search"),
    ctx: Context = None,
) -> str:
    """
    Check whether the legal elements of an NZ offense are satisfied by
    the provided facts. Returns a structured element-by-element analysis.
    """
    rag = _get_rag(ctx)
    result = rag.check_elements(
        offense=offense,
        facts=facts,
        statute=statute,
        collections=collections,
    )

    lines = [
        f"Offense: {result['offense']}",
        "",
        "Structured Elements:",
    ]
    for el in result.get("elements", []):
        status_icon = "✓" if el.get("proven") else "?" if el.get("unclear") else "✗"
        lines.append(
            f"  {status_icon} {el['element']}: {el['status']}"
        )
    lines.append("")
    lines.append("Full Analysis:")
    lines.append(result.get("analysis", "N/A"))
    return "\n".join(lines)


@mcp.tool()
def list_collections(ctx: Context = None) -> str:
    """List available legal database collections and their document counts."""
    rag = _get_rag(ctx)
    stats = rag.get_database_stats()
    lines = ["Available collections:\n"]
    for name, info in stats.get("collections", {}).items():
        lines.append(f"  • {name}: {info.get('count', 0)} docs – {info.get('description', '')}")
    lines.append(f"\nTotal documents: {stats.get('total_documents', 0)}")
    return "\n".join(lines)


@mcp.tool()
def get_database_stats(ctx: Context = None) -> str:
    """Get high-level statistics about the NZ Legal RAG database."""
    rag = _get_rag(ctx)
    stats = rag.get_database_stats()
    return json.dumps(stats, indent=2)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------
@mcp.resource("legal://collections")
def collections_resource() -> str:
    """Static resource listing all collection names."""
    return json.dumps(
        {
            "collections": [
                {"id": k, "description": v}
                for k, v in NZLegalRAG.COLLECTIONS.items()
            ]
        },
        indent=2,
    )


@mcp.resource("legal://status")
def status_resource() -> str:
    """Static resource showing server status."""
    return json.dumps(
        {
            "server": "nz-legal-rag-mcp",
            "version": "1.1.0",
            "transport": MCP_TRANSPORT,
            "models": {"llm": LLM_MODEL, "embedding": EMBEDDING_MODEL},
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------
@mcp.prompt()
def charge_review_prompt(charge_description: str) -> str:
    """Prompt template for reviewing a criminal charge."""
    return (
        f"Please review the following criminal charge under New Zealand law.\n\n"
        f"Charge: {charge_description}\n\n"
        f"Provide:\n"
        f"1. The legal elements of the offense\n"
        f"2. Evidence required to prove each element\n"
        f"3. Potential defenses\n"
        f"4. Relevant legislation sections\n"
        f"5. Case law references"
    )


@mcp.prompt()
def search_warrant_review_prompt(warrant_details: str) -> str:
    """Prompt template for reviewing a search warrant."""
    return (
        f"Please review the following search warrant under New Zealand law.\n\n"
        f"Warrant details: {warrant_details}\n\n"
        f"Assess:\n"
        f"1. Validity of the search authority\n"
        f"2. Compliance with s21 NZBORA and Search and Surveillance Act 2012\n"
        f"3. Procedural deficiencies\n"
        f"4. 'Reasonable grounds' evaluation\n"
        f"5. Potential remedies"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    import argparse

    parser = argparse.ArgumentParser(description="NZ Legal RAG MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "http"],
        default=MCP_TRANSPORT,
        help="Transport protocol",
    )
    parser.add_argument("--host", default=MCP_HOST, help="HTTP/SSE host")
    parser.add_argument("--port", type=int, default=MCP_PORT, help="HTTP/SSE port")
    parser.add_argument("--path", default=MCP_PATH, help="HTTP endpoint path")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run(transport="stdio")
    elif args.transport in ("sse", "streamable-http", "http"):
        # FastMCP.run() is sync; for HTTP we call run() with kwargs
        mcp.run(
            transport="streamable-http" if args.transport in ("http", "streamable-http") else "sse",
            host=args.host,
            port=args.port,
            path=args.path,
        )
    else:
        raise ValueError(f"Unknown transport: {args.transport}")


if __name__ == "__main__":
    main()
