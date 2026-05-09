#!/usr/bin/env python3
"""
NZ Legal RAG API Server
FastAPI-based REST API for legal research
"""

import os
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime
from contextlib import asynccontextmanager

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from core.rag_engine import NZLegalRAG, LegalAnalysis
from security.tenant_manager import TenantManager, AccessTier, TenantConfig

# Global instances
rag_engine: Optional[NZLegalRAG] = None
tenant_manager: Optional[TenantManager] = None

# Security
security = HTTPBearer(auto_error=False)


# Pydantic models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Search query")
    collections: Optional[List[str]] = Field(
        default=None, 
        description="Collections to search (default: all)"
    )
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total: int
    collections_searched: List[str]


class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=10, description="Legal question or scenario")
    analysis_type: str = Field(
        default="general",
        description="Type of analysis: general, charge_review, search_warrant, disclosure_review"
    )
    context: Optional[str] = Field(
        default=None,
        description="Additional context or facts"
    )


class AnalysisResponse(BaseModel):
    query: str
    answer: str
    citations: List[str]
    confidence: float
    analysis_type: str
    sources: List[Dict[str, Any]]
    timestamp: str


class SimilarCasesRequest(BaseModel):
    facts: str = Field(..., min_length=20, description="Case facts")
    legal_issue: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class ElementCheckRequest(BaseModel):
    offense: str = Field(..., description="Name of offense")
    facts: str = Field(..., description="Facts to check against elements")
    statute: Optional[str] = None


class TenantInfo(BaseModel):
    tenant_id: str
    name: str
    tier: str
    quotas: Dict[str, Any]


class UsageReport(BaseModel):
    tenant_id: str
    period_days: int
    summary: Dict[str, Any]
    daily_breakdown: List[Dict[str, Any]]


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global rag_engine, tenant_manager
    
    # Startup
    print("Starting NZ Legal RAG API Server...")
    
    # Initialize RAG engine
    rag_engine = NZLegalRAG(
        db_path=os.getenv("CHROMA_DB_PATH", "./chroma_db"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
        llm_model=os.getenv("LLM_MODEL", "mixtral:latest"),
        use_local_llm=True
    )
    
    # Initialize tenant manager
    tenant_manager = TenantManager(
        storage_dir=os.getenv("TENANT_DATA_PATH", "./tenant_data")
    )
    
    print(f"✓ Loaded {rag_engine.get_database_stats()['total_documents']} documents")
    print(f"✓ {len(tenant_manager.tenants)} tenants configured")
    
    yield
    
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="NZ Legal RAG API",
    description="New Zealand Legal Research API with RAG capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Authentication
def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TenantConfig:
    """Extract and verify tenant from API key"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    tenant = tenant_manager.verify_api_key(credentials.credentials)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key"
        )
    
    # Check expiration
    if tenant.expires_at:
        expires = datetime.fromisoformat(tenant.expires_at)
        if datetime.now() > expires:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired"
            )
    
    return tenant


def check_quota(tenant: TenantConfig, operation: str):
    """Check if tenant has quota for operation"""
    allowed, reason = tenant_manager.check_quota(tenant.tenant_id, operation)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=reason
        )


def require_tier(min_tier: AccessTier):
    """Require minimum tier for endpoint"""
    def checker(tenant: TenantConfig = Depends(get_current_tenant)):
        tier_levels = {
            AccessTier.COMMUNITY: 1,
            AccessTier.PROFESSIONAL: 2,
            AccessTier.ENTERPRISE: 3
        }
        
        if tier_levels[tenant.tier] < tier_levels[min_tier]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {min_tier.value} tier or higher"
            )
        return tenant
    return checker


# Endpoints
@app.get("/")
def root():
    """Root endpoint"""
    return {
        "name": "NZ Legal RAG API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    stats = rag_engine.get_database_stats()
    return {
        "status": "healthy",
        "database": stats,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/v1/collections")
def list_collections():
    """List available collections"""
    return {
        "collections": [
            {
                "id": name,
                "description": desc,
                "document_count": rag_engine.collections.get(name, {}).count() 
                    if name in rag_engine.collections else 0
            }
            for name, desc in NZLegalRAG.COLLECTIONS.items()
        ]
    }


@app.post("/api/v1/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    tenant: TenantConfig = Depends(get_current_tenant)
):
    """Search the legal database"""
    check_quota(tenant, "query")
    
    # Apply tenant filter
    if tenant.tier == AccessTier.COMMUNITY:
        # Community tier can only access public collections
        pass
    
    results = rag_engine.search(
        query=request.query,
        collections=request.collections,
        filters=request.filters,
        top_k=request.top_k
    )
    
    # Record usage
    tenant_manager.record_usage(tenant.tenant_id, query_count=1)
    
    return {
        "query": request.query,
        "results": [
            {
                "document": r.document[:500],
                "metadata": r.metadata,
                "relevance": round(r.relevance, 4)
            }
            for r in results
        ],
        "total": len(results),
        "collections_searched": request.collections or list(rag_engine.collections.keys())
    }


@app.post("/api/v1/analyze", response_model=AnalysisResponse)
def analyze(
    request: AnalysisRequest,
    tenant: TenantConfig = Depends(get_current_tenant)
):
    """Perform AI-powered legal analysis"""
    check_quota(tenant, "query")
    
    # Combine query with context if provided
    full_query = request.query
    if request.context:
        full_query = f"{request.query}\n\nContext: {request.context}"
    
    analysis = rag_engine.legal_analysis(
        query=full_query,
        analysis_type=request.analysis_type
    )
    
    # Record usage
    tenant_manager.record_usage(tenant.tenant_id, query_count=1)
    
    return {
        "query": request.query,
        "answer": analysis.answer,
        "citations": analysis.citations,
        "confidence": analysis.confidence,
        "analysis_type": analysis.analysis_type,
        "sources": [
            {
                "title": s.metadata.get("title", "Unknown"),
                "category": s.metadata.get("category", "Unknown"),
                "relevance": round(s.relevance, 4)
            }
            for s in analysis.sources
        ],
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v1/similar-cases")
def find_similar_cases(
    request: SimilarCasesRequest,
    tenant: TenantConfig = Depends(get_current_tenant)
):
    """Find cases with similar fact patterns"""
    check_quota(tenant, "query")
    
    results = rag_engine.find_similar_cases(
        facts=request.facts,
        legal_issue=request.legal_issue,
        top_k=request.top_k
    )
    
    # Record usage
    tenant_manager.record_usage(tenant.tenant_id, query_count=1)
    
    return {
        "facts": request.facts,
        "legal_issue": request.legal_issue,
        "results": [
            {
                "title": r.metadata.get("title", "Unknown"),
                "citation": r.metadata.get("citation", ""),
                "court": r.metadata.get("court", "Unknown"),
                "year": r.metadata.get("year"),
                "relevance": round(r.relevance, 4),
                "summary": r.document[:500]
            }
            for r in results
        ]
    }


@app.post("/api/v1/check-elements")
def check_elements(
    request: ElementCheckRequest,
    tenant: TenantConfig = Depends(get_current_tenant)
):
    """Check if legal elements are satisfied by facts"""
    check_quota(tenant, "query")
    
    result = rag_engine.check_elements(
        offense=request.offense,
        facts=request.facts,
        statute=request.statute
    )
    
    # Record usage
    tenant_manager.record_usage(tenant.tenant_id, query_count=1)
    
    return result


@app.get("/api/v1/tenant/me", response_model=TenantInfo)
def get_my_tenant(tenant: TenantConfig = Depends(get_current_tenant)):
    """Get current tenant information"""
    return {
        "tenant_id": tenant.tenant_id,
        "name": tenant.name,
        "tier": tenant.tier.value,
        "quotas": {
            "max_queries_per_day": tenant.max_queries_per_day,
            "max_storage_bytes": tenant.max_storage_bytes,
            "max_documents": tenant.max_documents,
            "queries_per_minute": tenant.queries_per_minute
        }
    }


@app.get("/api/v1/tenant/usage", response_model=UsageReport)
def get_usage(
    days: int = 30,
    tenant: TenantConfig = Depends(get_current_tenant)
):
    """Get usage report for current tenant"""
    report = tenant_manager.get_usage_report(tenant.tenant_id, days)
    
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    
    return {
        "tenant_id": report["tenant_id"],
        "period_days": report["period_days"],
        "summary": report["summary"],
        "daily_breakdown": report["daily_breakdown"]
    }


# Admin endpoints (would need additional admin auth)
@app.get("/api/v1/admin/tenants")
def list_tenants(admin_key: str):
    """List all tenants (admin only)"""
    # Simple admin check - in production use proper auth
    expected = os.getenv("ADMIN_API_KEY")
    if not expected or admin_key != expected:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return {"tenants": tenant_manager.list_tenants()}


# Error handlers
@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "Please try again later"
        }
    )


def main():
    """Run the API server"""
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    reload = os.getenv("API_RELOAD", "false").lower() == "true"
    
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
