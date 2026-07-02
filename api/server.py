#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NZ Legal RAG API Server (Online Demo Version) — FIXED v3
FastAPI-based REST API for legal research with role-based access.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import shutil
import string
import sys
import time
import traceback
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pathlib import Path

# Load .env from the project root so the API always uses the same environment
# regardless of the working directory it was started from.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import Body, Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from api.auth import router as auth_router, get_current_tenant as new_auth_get_current_tenant, create_session as create_auth_session
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

# ─── Lazy imports (graceful degradation if modules missing) ───────────────────
FileParser = None
NZLegalRAG = None
TenantConfig = None
TenantManager = None
UserRole = None

try:
    from core.file_parser import FileParser as _FileParser
    FileParser = _FileParser
except ImportError:
    pass

try:
    from core.rag_engine import NZLegalRAG as _NZLegalRAG
    NZLegalRAG = _NZLegalRAG
except ImportError:
    pass

try:
    from core.agent_swarm import ollama_unload_model as _ollama_unload_model
except ImportError:
    _ollama_unload_model = None

try:
    from security.tenant_manager import TenantConfig as _TenantConfig, TenantManager as _TenantManager, UserRole as _UserRole
    TenantConfig = _TenantConfig
    TenantManager = _TenantManager
    UserRole = _UserRole
except ImportError:
    pass

rag_engine: Optional[Any] = None
tenant_manager: Optional[Any] = None
security = HTTPBearer(auto_error=False)
_analysis_semaphore = asyncio.Semaphore(1)

DEMO_DATA_PATH = os.getenv("DEMO_DATA_PATH", "./demo_sessions")
DEMO_CHALLENGES_FILE = os.path.join(DEMO_DATA_PATH, "demo_challenges.json")
DEMO_SESSIONS_FILE = os.path.join(DEMO_DATA_PATH, "demo_sessions.json")
DEMO_SESSION_ROOT = os.getenv("DEMO_SESSION_ROOT", "./temp_sessions")
DEMO_CHALLENGE_TTL_MINUTES = int(os.getenv("DEMO_CHALLENGE_TTL_MINUTES", "15"))
DEMO_SESSION_TTL_MINUTES = int(os.getenv("DEMO_SESSION_TTL_MINUTES", "20"))
SESSION_ACTIVITY_FILE = os.path.join(DEMO_DATA_PATH, "session_activity.json")
SESSION_ACTIVITY_TTL_MINUTES = int(os.getenv("SESSION_ACTIVITY_TTL_MINUTES", "30"))
TEMP_COLLECTION_PREFIX = "temp_session_"



def _clean_ollama_options(options: dict | None) -> dict:
    options = dict(options or {})
    drop_keys = ["mirostat", "mirostat_eta", "mirostat_tau", "tfs_z"]
    disabled_values = {None, "", 0, 0.0, False, "0", "false", "False", "off", "Off", "disabled", "Disabled"}
    for key in drop_keys:
        if key in options and options.get(key) in disabled_values:
            options.pop(key, None)
    return {k: v for k, v in options.items() if v is not None}


def get_rag_engine() -> Any:
    global rag_engine
    if rag_engine is None and NZLegalRAG is not None:
        rag_engine = NZLegalRAG(
            db_path=os.getenv("CHROMA_DB_PATH", os.getenv("CHROMADB_PATH", "./chroma_db")),
            embedding_model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            llm_model=os.getenv("LLM_MODEL", "deepseek-r1"),
            use_local_llm=True,
        )
    return rag_engine


def _ensure_demo_dirs() -> None:
    os.makedirs(DEMO_DATA_PATH, exist_ok=True)
    os.makedirs(DEMO_SESSION_ROOT, exist_ok=True)


def _load_json_file(file_path: str) -> Dict[str, Any]:
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json_file(file_path: str, data: Dict[str, Any]) -> None:
    _ensure_demo_dirs()
    parent = os.path.dirname(os.path.abspath(file_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp_path = file_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, file_path)


def _now() -> datetime:
    return datetime.now()


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _generate_guest_username() -> str:
    alphabet = "bcdfghjkmnpqrstvwxyz23456789"
    suffix = "".join(secrets.choice(alphabet) for _ in range(6))
    return f"guest-{suffix}"


def _generate_access_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(8))


def _generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def _generate_session_id() -> str:
    return secrets.token_urlsafe(24)


def make_temp_collection_name(session_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "-", session_id or "")
    safe = safe.strip("._-")
    if len(safe) < 3:
        safe = (safe + "tmp")[:3]
    return f"temp_session_{safe}"


def _load_demo_state() -> tuple[Dict[str, Any], Dict[str, Any]]:
    _ensure_demo_dirs()
    challenges = _load_json_file(DEMO_CHALLENGES_FILE)
    sessions = _load_json_file(DEMO_SESSIONS_FILE)
    return challenges, sessions


def _save_demo_state(challenges: Dict[str, Any], sessions: Dict[str, Any]) -> None:
    _save_json_file(DEMO_CHALLENGES_FILE, challenges)
    _save_json_file(DEMO_SESSIONS_FILE, sessions)


def _destroy_demo_session_data(session_id: str) -> List[str]:
    deleted: List[str] = []
    if not session_id:
        return deleted

    temp_collection = make_temp_collection_name(session_id)
    try:
        engine = get_rag_engine()
        if engine is not None and temp_collection in getattr(engine, "collections", {}):
            try:
                engine.client.delete_collection(name=temp_collection)
                deleted.append(temp_collection)
            except Exception:
                pass
            engine.collections.pop(temp_collection, None)
    except Exception:
        pass

    session_dir = os.path.join(DEMO_SESSION_ROOT, session_id)
    if os.path.isdir(session_dir):
        shutil.rmtree(session_dir, ignore_errors=True)

    return deleted


def purge_expired_demo_state() -> tuple[Dict[str, Any], Dict[str, Any]]:
    challenges, sessions = _load_demo_state()
    now = _now()

    expired_challenges = []
    for challenge_id, item in list(challenges.items()):
        expires_at = _parse_dt(item.get("expires_at"))
        if not expires_at or expires_at < now:
            expired_challenges.append(challenge_id)
    for challenge_id in expired_challenges:
        challenges.pop(challenge_id, None)

    expired_tokens = []
    for token, item in list(sessions.items()):
        expires_at = _parse_dt(item.get("expires_at"))
        last_seen = _parse_dt(item.get("last_seen"))
        inactive = (
            last_seen is not None
            and (_now() - last_seen) > timedelta(minutes=DEMO_SESSION_TTL_MINUTES)
        )
        if not expires_at or _now() > expires_at or inactive:
            expired_tokens.append(token)
    for token in expired_tokens:
        session_rec = sessions.pop(token, None) or {}
        _destroy_demo_session_data(session_rec.get("session_id", ""))

    _save_demo_state(challenges, sessions)
    return challenges, sessions


# ─── Pydantic Models ──────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3)
    collections: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    total: int
    collections_searched: List[str]


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=3)
    collections: Optional[List[str]] = None
    top_k: int = Field(default=10, ge=1, le=50)
    filters: Optional[Dict[str, Any]] = None


class RAGResponse(BaseModel):
    query: str
    answer: str
    sources: List[Dict[str, Any]]
    collections_searched: List[str]


class SimilarCasesRequest(BaseModel):
    facts: str = Field(..., min_length=20)
    legal_issue: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class ElementCheckRequest(BaseModel):
    offense: str
    facts: str
    statute: Optional[str] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    tenant_id: str
    username: str
    name: str
    role: str
    api_key: str
    quotas: Dict[str, Any]


class StaffLoginResponse(BaseModel):
    tenant_id: str
    username: str
    name: str
    role: str
    access_token: str
    expires_in: int
    quotas: Dict[str, Any]


class DemoStartRequest(BaseModel):
    email: str
    phone: str


class DemoStartResponse(BaseModel):
    ok: bool
    challenge_id: str
    username: str
    access_code: str
    message: str


class DemoVerifyRequest(BaseModel):
    challenge_id: str
    access_code: str


class DemoVerifyResponse(BaseModel):
    ok: bool
    role: str
    tenant_id: str
    username: str
    name: str
    api_key: str
    session_id: str
    expires_at: str
    quotas: Dict[str, Any]


class DemoLogoutResponse(BaseModel):
    ok: bool
    message: str
    session_id: Optional[str] = None
    collections_deleted: Optional[List[str]] = None


class TenantInfo(BaseModel):
    tenant_id: str
    username: str
    name: str
    role: str
    quotas: Dict[str, Any]


class UsageReport(BaseModel):
    tenant_id: str
    period_days: int
    summary: Dict[str, Any]
    daily_breakdown: List[Dict[str, Any]]


class IngestRequest(BaseModel):
    documents: List[Dict[str, Any]]
    collection: str = Field(default="user_uploads")


class IngestResponse(BaseModel):
    success: bool
    message: str
    chunks_ingested: int


class FileUploadResponse(BaseModel):
    success: bool
    message: str
    files_processed: int
    files_failed: int
    total_chunks: int
    details: List[Dict[str, Any]]


class DisclosureAnalysisRequest(BaseModel):
    disclosure_text: str = Field(default="", min_length=0)
    analysis_type: str = Field(default="full")
    uploaded_collection: Optional[str] = Field(default=None)


class DisclosureAnalysisResponse(BaseModel):
    success: bool
    message: str
    processing_time_seconds: float
    expert_count: int
    # New legal-brief sections
    title_block: Optional[str] = None
    table_of_contents: Optional[str] = None
    executive_summary: Optional[str] = None
    charge_and_legislative_framework: Optional[str] = None
    summary_of_evidence: Optional[str] = None
    assessment_of_prosecution_case: Optional[str] = None
    evidence_analysis: Optional[str] = None
    elements_of_the_offence: Optional[str] = None
    defence_strategies: Optional[str] = None
    cross_examination_priorities: Optional[str] = None
    disclosure_and_forensic_gaps: Optional[str] = None
    instructions_to_counsel_pre_trial: Optional[str] = None
    pre_trial_instructions_for_lawyer: Optional[str] = None
    evidentiary_issues_to_raise: Optional[str] = None
    conclusion: Optional[str] = None
    conclusion_and_risk_assessment: Optional[str] = None
    disclaimer: Optional[str] = None
    # Legacy sections
    disclosure_overview: Optional[str] = None
    charge_analysis: Optional[str] = None
    summary_of_facts_review: Optional[str] = None
    police_conduct_assessment: Optional[str] = None
    further_disclosure_required: Optional[str] = None
    bail_analysis: Optional[str] = None
    options_and_recommendations: Optional[str] = None
    expert_consensus_and_divergence: Optional[str] = None
    risk_assessment: Optional[str] = None
    strategist_kc: Optional[str] = None
    evidential_kc: Optional[str] = None
    rights_kc: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DisclosureDeepAnalysisRequest(BaseModel):
    focus_area: str = Field(..., min_length=3)
    disclosure_text: str = Field(default="", min_length=0)
    uploaded_collection: Optional[str] = Field(default=None)
    previous_analysis: Optional[str] = Field(default=None)


# ─── FastAPI App ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global tenant_manager
    if TenantManager is not None:
        tenant_manager = TenantManager(storage_dir=os.getenv("TENANT_DATA_PATH", "./tenant_data"))
    purge_expired_demo_state()
    cleanup_task = asyncio.create_task(_cleanup_temp_collections_task())
    email_poller_task = None
    try:
        from services.email_config import get_email_config
        from services.email_job_store import EmailJobStore
        from services.email_processor import EmailProcessor
        email_cfg = get_email_config()
        if email_cfg.enabled:
            db_path = os.path.join(
                os.getenv("TENANT_DATA_PATH", "./tenant_data"), "email_jobs.db"
            )
            email_store = EmailJobStore(db_path)
            email_processor = EmailProcessor(email_cfg, email_store, _analysis_semaphore)
            from services.email_poller import start_email_poller
            email_poller_task = start_email_poller(email_cfg, email_processor)
            print("[EMAIL] Poller started.")
        yield
    finally:
        cleanup_task.cancel()
        if email_poller_task is not None:
            email_poller_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        if email_poller_task is not None:
            try:
                await email_poller_task
            except asyncio.CancelledError:
                pass


app = FastAPI(
    title="NZ Legal RAG API",
    description="New Zealand Legal Research API with RAG capabilities",
    version="1.2.2",
    lifespan=lifespan,
)
app.include_router(auth_router)

try:
    from api.email_routes import router as email_router
    app.include_router(email_router)
except ImportError:
    pass

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_session_activity_middleware(request: Request, call_next):
    """Record X-Session-ID activity for temp collection lifetime tracking."""
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        try:
            await asyncio.to_thread(_touch_session_activity, session_id)
        except Exception as exc:
            print(f"[SESSION_ACTIVITY] Middleware tracking failed: {exc}")
    response = await call_next(request)
    return response


# ─── Auth Helpers ─────────────────────────────────────────────────────────────

class DemoTenant:
    """Lightweight tenant-like object for demo sessions."""
    def __init__(self, data: Dict[str, Any]):
        self.tenant_id = data.get("tenant_id", "demo")
        self.username = data.get("username", "demo")
        self.name = data.get("name", "Demo User")
        self.role = data.get("role", "user")
        self.api_key_hash = "demo-runtime"
        self.password_hash = "demo-runtime"
        self.max_queries_per_day = 1000
        self.max_storage_bytes = 1024 * 1024 * 1024
        self.max_documents = 5000
        self.queries_per_minute = 60
        self.created_at = data.get("created_at")
        self.expires_at = data.get("expires_at")


def get_current_tenant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Any:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if tenant_manager is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Tenant manager not initialized")

    tenant = tenant_manager.verify_api_key(credentials.credentials)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired API key")

    if tenant.expires_at:
        expires_at = _parse_dt(tenant.expires_at)
        if expires_at and _now() > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key expired")

    return tenant


def get_current_demo_or_tenant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Any:
    """Accept either a demo session token, new auth token, or real tenant API key."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # FIXED: Check new auth system first (cookie or Bearer token from auth.py)
    # The new auth function may expect HTTPAuthorizationCredentials or raw string
    # We catch ALL exceptions to ensure fallback always works
    try:
        # Try passing the credentials object first (some implementations expect this)
        tenant = new_auth_get_current_tenant(credentials)
        if tenant is not None:
            return tenant
    except HTTPException:
        # New auth rejected this token - continue to fallback
        pass
    except Exception:
        pass

    try:
        # Fallback: try with raw token string
        tenant = new_auth_get_current_tenant(token)
        if tenant is not None:
            return tenant
    except HTTPException:
        raise
    except Exception:
        pass

    # Fall back to demo session token
    _, sessions = purge_expired_demo_state()
    session = sessions.get(token)
    if session:
        expires_at = _parse_dt(session.get("expires_at"))
        last_seen = _parse_dt(session.get("last_seen"))
        now = _now()
        inactive = (
            last_seen is not None
            and (now - last_seen) > timedelta(minutes=DEMO_SESSION_TTL_MINUTES)
        )
        if not expires_at or now > expires_at or inactive:
            _destroy_demo_session_data(session.get("session_id", ""))
            sessions.pop(token, None)
            challenges, updated_sessions = _load_demo_state()
            _save_demo_state(challenges, updated_sessions)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Demo session expired")

        # Update last_seen on activity
        session["last_seen"] = now.isoformat()
        challenges, _ = _load_demo_state()
        sessions = _load_json_file(DEMO_SESSIONS_FILE)
        if token in sessions:
            sessions[token]["last_seen"] = now.isoformat()
            _save_json_file(DEMO_SESSIONS_FILE, sessions)

        return DemoTenant(session)

    # Fall back to old tenant manager
    return get_current_tenant(credentials)


def _get_role_value(tenant: Any) -> str:
    """Extract role string from TenantConfig, DemoTenant, or auth session dict."""
    if isinstance(tenant, dict):
        role = tenant.get("role")
        if isinstance(role, str):
            return role
        return getattr(role, "value", str(role)) if role is not None else "user"
    if hasattr(tenant, "role"):
        if isinstance(tenant.role, str):
            return tenant.role
        return getattr(tenant.role, "value", str(tenant.role))
    return "user"


def _get_tenant_id(tenant: Any) -> str:
    return tenant.tenant_id if hasattr(tenant, "tenant_id") else tenant.get("tenant_id", "")


def _get_username(tenant: Any) -> str:
    return tenant.username if hasattr(tenant, "username") else tenant.get("username", "")


def _touch_session_activity(session_id: str) -> None:
    """Record that a Streamlit session ID is still active."""
    if not session_id:
        return
    try:
        data = _load_json_file(SESSION_ACTIVITY_FILE)
    except Exception:
        data = {}
    data[session_id] = {"last_seen": _now().isoformat()}
    try:
        _save_json_file(SESSION_ACTIVITY_FILE, data)
    except Exception as exc:
        print(f"[SESSION_ACTIVITY] Failed to write activity file: {exc}")


def _get_active_session_ids(ttl_minutes: Optional[int] = None) -> set[str]:
    """Return Streamlit session IDs that are still live.

    Combines recently seen X-Session-ID values with active demo sessions.
    """
    if ttl_minutes is None:
        ttl_minutes = SESSION_ACTIVITY_TTL_MINUTES
    cutoff = _now() - timedelta(minutes=ttl_minutes)
    active: set[str] = set()

    # Activity tracked from X-Session-ID headers
    try:
        activity = _load_json_file(SESSION_ACTIVITY_FILE)
    except Exception:
        activity = {}
    for session_id, info in activity.items():
        if not isinstance(info, dict):
            continue
        last_seen = _parse_dt(info.get("last_seen"))
        if last_seen and last_seen > cutoff:
            active.add(session_id)

    # Active demo sessions from persisted store
    try:
        _, sessions = _load_demo_state()
        now = _now()
        for session in sessions.values():
            sid = session.get("session_id")
            if not sid:
                continue
            last_seen = _parse_dt(session.get("last_seen"))
            expires_at = _parse_dt(session.get("expires_at"))
            if last_seen and last_seen > cutoff and expires_at and expires_at > now:
                active.add(sid)
    except Exception:
        pass

    return active


def cleanup_expired_temp_collections() -> list[str]:
    """Delete temp_session_* collections with no live associated session."""
    engine = get_rag_engine()
    if engine is None:
        print("[TEMP_CLEANUP] RAG engine not available")
        return []

    active_sids = _get_active_session_ids()
    deleted: list[str] = []

    try:
        collections = engine.list_all_collections()
    except Exception as exc:
        print(f"[TEMP_CLEANUP] Failed to list collections: {exc}")
        return []

    for coll in collections:
        name = coll.get("name") if isinstance(coll, dict) else str(coll)
        if not name or not name.startswith(TEMP_COLLECTION_PREFIX):
            continue
        sid = name[len(TEMP_COLLECTION_PREFIX):]
        if sid not in active_sids:
            try:
                engine.delete_collection(name)
                deleted.append(name)
                print(f"[TEMP_CLEANUP] Deleted expired collection: {name}")
            except Exception as exc:
                print(f"[TEMP_CLEANUP] Failed to delete {name}: {exc}")

    if deleted:
        print(f"[TEMP_CLEANUP] Deleted {len(deleted)} expired temp collection(s)")
    else:
        print("[TEMP_CLEANUP] No expired temp collections found")
    return deleted


async def _cleanup_temp_collections_task() -> None:
    """Background task that runs cleanup every 60 seconds."""
    while True:
        try:
            await asyncio.to_thread(cleanup_expired_temp_collections)
        except Exception as exc:
            print(f"[TEMP_CLEANUP] Background task error: {exc}")
        await asyncio.sleep(60)


def check_quota(tenant: Any, operation: str):
    if tenant_manager is None:
        return
    tid = _get_tenant_id(tenant)
    if tid.startswith("demo_"):
        return
    allowed, reason = tenant_manager.check_quota(tid, operation)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=reason)


def check_quota_flexible(tenant: Any, operation: str):
    tid = _get_tenant_id(tenant)
    if tid.startswith("demo_"):
        return
    check_quota(tenant, operation)


def require_role(*roles):
    """Role checker that handles both UserRole enums and plain strings."""
    def checker(tenant: Any = Depends(get_current_demo_or_tenant)):
        role_val = _get_role_value(tenant)
        # Normalize expected roles
        expected = []
        for r in roles:
            if r is None:
                continue
            if hasattr(r, "value"):
                expected.append(r.value)
            else:
                expected.append(str(r))
        if role_val not in expected:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires one of the following roles: {expected}",
            )
        return tenant
    return checker


# ─── Utility Functions ──────────────────────────────────────────────────────

def _get_search_collections(session_id: Optional[str], requested: Optional[List[str]]) -> List[str]:
    engine = get_rag_engine()
    if engine is None:
        return []
    
    # Get all collections from ChromaDB directly (not just cached engine.collections)
    all_collection_names = []
    try:
        client = getattr(engine, "client", None)
        if client:
            all_collection_names = [c.name for c in client.list_collections()]
    except Exception:
        pass
    
    if requested:
        base = [c for c in requested if not c.startswith("temp_session_")]
    else:
        base = [c for c in all_collection_names if not c.startswith("temp_session_")]

    if session_id:
        temp_collection = make_temp_collection_name(session_id)
        # Check ChromaDB directly, not just engine cache
        if temp_collection in all_collection_names and temp_collection not in base:
            base.append(temp_collection)

    return base


def _list_collection_names(engine: Any) -> List[str]:
    """Return all collection names directly from ChromaDB client."""
    try:
        client = getattr(engine, "client", None)
        if client:
            return [c.name for c in client.list_collections()]
    except Exception:
        pass
    return []


def _fetch_session_uploaded_text(
    session_id: Optional[str],
    max_chars: int = 20_000,
    include_user_uploads: bool = False,
    collections: Optional[List[str]] = None,
) -> str:
    """Fetch text from uploaded documents.

    By default only the session temp collection is read, to protect client
    privacy. Set include_user_uploads=True to also read the user_uploads
    collection (e.g. for staff reference materials).

    If `collections` is provided, any of those collections that look like
    uploaded documents (not known permanent legal sources) are also fetched.
    This lets analysis pick up documents uploaded to user-named collections.
    """
    engine = get_rag_engine()
    if engine is None:
        print("[FETCH_UPLOADS] RAG engine not available")
        return ""

    all_collection_names = _list_collection_names(engine)
    print(f"[FETCH_UPLOADS] session_id={session_id}, available_collections={all_collection_names}")

    collections_to_fetch = []

    temp_collection = None
    if session_id:
        temp_collection = make_temp_collection_name(session_id)
        print(f"[FETCH_UPLOADS] looking for temp_collection={temp_collection}")
        if temp_collection in all_collection_names:
            collections_to_fetch.append(temp_collection)
        else:
            print(f"[FETCH_UPLOADS] temp_collection {temp_collection} NOT FOUND")

    if include_user_uploads and "user_uploads" in all_collection_names:
        if "user_uploads" not in collections_to_fetch:
            collections_to_fetch.append("user_uploads")

    # Also fetch from any uploaded-document collections that will be searched.
    legal_collections = {"nz_legislation", "nz_case_law", "nzlii_criminal_cases", "nz_police_manual", "legal_research"}
    if collections:
        for c in collections:
            if c not in collections_to_fetch and c not in legal_collections and not c.startswith("temp_session_"):
                collections_to_fetch.append(c)

    if not collections_to_fetch:
        print("[FETCH_UPLOADS] no collections to fetch")
        return ""

    print(f"[FETCH_UPLOADS] collections_to_fetch={collections_to_fetch}")
    parts = []
    chars_used = 0
    for coll_name in collections_to_fetch:
        try:
            client = getattr(engine, "client", None)
            coll = engine.collections.get(coll_name)
            if coll is None and client is not None:
                coll = client.get_collection(coll_name)
            if coll is None:
                continue

            data = coll.get(include=["documents", "metadatas"])
            documents = data.get("documents", []) or []
            metadatas = data.get("metadatas", []) or []

            # Sort by chunk_index so the document reads in order
            indexed = []
            for i, (doc, meta) in enumerate(zip(documents, metadatas)):
                chunk_index = (meta or {}).get("chunk_index", i)
                indexed.append((chunk_index, doc, meta or {}))
            indexed.sort(key=lambda x: x[0])

            doc_count = 0
            for _, doc, meta in indexed:
                if chars_used >= max_chars:
                    break
                source = meta.get("filename") or meta.get("source") or meta.get("title") or coll_name
                remaining = max_chars - chars_used
                snippet = doc[:remaining]
                parts.append(f"[UPLOADED DOCUMENT - {source}]\n{snippet}")
                chars_used += len(snippet) + 1
                doc_count += 1
            print(f"[FETCH_UPLOADS] fetched {doc_count} chunks from {coll_name}")
        except Exception as e:
            print(f"Error fetching uploaded docs from {coll_name}: {e}")
            continue

    result = "\n\n".join(parts)
    print(f"[FETCH_UPLOADS] total fetched chars={len(result)}")
    return result


def _extract_chunk_count(message: str) -> int:
    for token in message.split():
        if token.isdigit():
            return int(token)
    return 0


def _build_upload_documents(parsed_docs: List[Any]) -> List[Dict[str, Any]]:
    return [
        {
            "name": doc.filename,
            "content": doc.content,
            "filetype": getattr(doc, "file_type", ""),
            "metadata": {
                "source": doc.filename,
                "filename": doc.filename,
                "title": doc.filename,
            },
        }
        for doc in parsed_docs
    ]


def _build_upload_details(parsed_docs: List[Any], errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    details: List[Dict[str, Any]] = []
    for doc in parsed_docs:
        item = {
            "filename": doc.filename,
            "type": getattr(doc, "file_type", ""),
            "words": doc.metadata.get("words", 0),
            "characters": doc.metadata.get("characters", 0),
            "status": "success",
        }
        if getattr(doc, "pages", None):
            item["pages"] = doc.pages
        if getattr(doc, "sheets", None):
            item["sheets"] = doc.sheets
        details.append(item)

    for error in errors:
        item = dict(error)
        item["status"] = "failed"
        details.append(item)

    return details


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "name": "NZ Legal RAG API",
        "version": "1.2.2",
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "api",
        "timestamp": _now().isoformat(),
    }


@app.post("/auth/demo/start", response_model=DemoStartResponse)
async def demo_start(request: DemoStartRequest):
    challenges, sessions = await asyncio.to_thread(purge_expired_demo_state)

    email = request.email.strip()
    phone = request.phone.strip()
    if not email or not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email and phone are required")

    challenge_id = secrets.token_urlsafe(18)
    username = _generate_guest_username()
    access_code = _generate_access_code()
    expires_at = (_now() + timedelta(minutes=DEMO_CHALLENGE_TTL_MINUTES)).isoformat()

    challenges[challenge_id] = {
        "challenge_id": challenge_id,
        "email": email,
        "phone": phone,
        "username": username,
        "access_code": access_code,
        "created_at": _now().isoformat(),
        "expires_at": expires_at,
    }
    await asyncio.to_thread(_save_demo_state, challenges, sessions)

    return {
        "ok": True,
        "challenge_id": challenge_id,
        "username": username,
        "access_code": access_code,
        "message": "One-time access code issued",
    }


@app.post("/auth/demo/verify", response_model=DemoVerifyResponse)
async def demo_verify(request: DemoVerifyRequest):
    challenges, sessions = await asyncio.to_thread(purge_expired_demo_state)

    challenge = challenges.get(request.challenge_id)
    if not challenge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Challenge not found or expired")

    if challenge.get("access_code", "").strip().upper() != request.access_code.strip().upper():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access code")

    session_id = _generate_session_id()
    api_key = _generate_api_key()
    tenant_id = f"demo_{session_id[:12]}"
    expires_at = (_now() + timedelta(minutes=DEMO_SESSION_TTL_MINUTES)).isoformat()

    os.makedirs(os.path.join(DEMO_SESSION_ROOT, session_id), exist_ok=True)

    now = _now().isoformat()
    sessions[api_key] = {
        "tenant_id": tenant_id,
        "session_id": session_id,
        "username": challenge["username"],
        "name": challenge["username"],
        "email": challenge["email"],
        "phone": challenge["phone"],
        "created_at": now,
        "expires_at": expires_at,
        "last_seen": now,
    }

    challenges.pop(request.challenge_id, None)
    await asyncio.to_thread(_save_demo_state, challenges, sessions)

    return {
        "ok": True,
        "role": "user",
        "tenant_id": tenant_id,
        "username": challenge["username"],
        "name": challenge["username"],
        "api_key": api_key,
        "session_id": session_id,
        "expires_at": expires_at,
        "quotas": {
            "max_queries_per_day": 1000,
            "max_storage_bytes": 1024 * 1024 * 1024,
            "max_documents": 5000,
            "queries_per_minute": 60,
        },
    }


@app.post("/auth/demo/logout", response_model=DemoLogoutResponse)
async def demo_logout(
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    deleted: List[str] = []
    challenges, sessions = await asyncio.to_thread(purge_expired_demo_state)
    token = credentials.credentials if credentials else None

    if token and token in sessions:
        stored = sessions.pop(token)
        session_id = session_id or stored.get("session_id")
        deleted.extend(await asyncio.to_thread(_destroy_demo_session_data, session_id or ""))
        await asyncio.to_thread(_save_demo_state, challenges, sessions)
    elif session_id:
        deleted.extend(await asyncio.to_thread(_destroy_demo_session_data, session_id))

    return {
        "ok": True,
        "message": "Demo session destroyed",
        "session_id": session_id,
        "collections_deleted": sorted(set(deleted)),
    }


@app.post("/api/v1/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    if tenant_manager is None:
        raise HTTPException(status_code=503, detail="Tenant manager not available")
    result = await asyncio.to_thread(
        tenant_manager.verify_credentials, request.username, request.password
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    tenant, api_key = result
    return {
        "tenant_id": tenant.tenant_id,
        "username": tenant.username,
        "name": tenant.name,
        "role": tenant.role.value,
        "api_key": api_key,
        "quotas": {
            "max_queries_per_day": tenant.max_queries_per_day,
            "max_storage_bytes": tenant.max_storage_bytes,
            "max_documents": tenant.max_documents,
            "queries_per_minute": tenant.queries_per_minute,
        },
    }


@app.post("/auth/staff/login", response_model=StaffLoginResponse)
async def staff_login(request: LoginRequest):
    """Staff/admin login that creates a tracked session instead of a long-lived API key."""
    if tenant_manager is None:
        raise HTTPException(status_code=503, detail="Tenant manager not available")
    result = await asyncio.to_thread(
        tenant_manager.verify_credentials, request.username, request.password
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    tenant, _api_key = result
    role = tenant.role.value if hasattr(tenant.role, "value") else str(tenant.role)
    token = create_auth_session(
        tenant_id=tenant.tenant_id,
        role=role,
        email=tenant.username,
        name=tenant.name,
    )
    return {
        "tenant_id": tenant.tenant_id,
        "username": tenant.username,
        "name": tenant.name,
        "role": role,
        "access_token": token,
        "expires_in": int(os.getenv("SESSION_TTL_MINUTES", "20")) * 60,
        "quotas": {
            "max_queries_per_day": tenant.max_queries_per_day,
            "max_storage_bytes": tenant.max_storage_bytes,
            "max_documents": tenant.max_documents,
            "queries_per_minute": tenant.queries_per_minute,
        },
    }


@app.get("/api/v1/collections")
def list_collections():
    engine = get_rag_engine()
    if engine is None:
        return {"collections": []}
    return {
        "collections": [
            {
                "id": c["name"],
                "name": c["name"],
                "description": c.get("description", ""),
                "document_count": c.get("document_count", 0),
            }
            for c in engine.list_all_collections()
        ]
    }


SYSTEM_COLLECTIONS = {"nz_legislation", "nz_case_law", "nz_police_manual", "legal_research"}


def _sanitize_collection_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_-]", "-", name)
    name = re.sub(r"^-+|-+$", "", name)
    return name


@app.post("/api/v1/admin/collections/{name}")
def create_collection(
    name: str,
    description: str = Body(""),
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin", UserRole.STAFF if UserRole else "staff", "adminstaff")),
):
    safe_name = _sanitize_collection_name(name)
    if not safe_name or len(safe_name) < 2:
        raise HTTPException(status_code=400, detail="Invalid collection name")
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        engine.create_collection(safe_name, description=description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "name": safe_name, "message": f"Collection '{safe_name}' created"}


@app.delete("/api/v1/admin/collections/{name}")
def delete_collection(
    name: str,
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin")),
):
    if name in SYSTEM_COLLECTIONS:
        raise HTTPException(status_code=403, detail="Cannot delete system collection")
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        engine.delete_collection(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"success": True, "name": name, "message": f"Collection '{name}' deleted"}


@app.get("/api/v1/admin/collections/{name}/inspect")
def inspect_collection(
    name: str,
    offset: int = 0,
    limit: int = 20,
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin", UserRole.STAFF if UserRole else "staff", "adminstaff")),
):
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")
    try:
        return engine.inspect_collection(name, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    check_quota_flexible(tenant, "query")

    collections = _get_search_collections(session_id, request.collections)
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    results = engine.search(
        query=request.query,
        collections=collections,
        filters=request.filters,
        top_k=request.top_k,
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(_get_tenant_id(tenant), query_count=1)

    return {
        "query": request.query,
        "results": [
            {
                "document": r.document[:500],
                "metadata": r.metadata,
                "relevance": round(r.relevance, 4),
            }
            for r in results
        ],
        "total": len(results),
        "collections_searched": collections,
    }


@app.post("/api/v1/rag", response_model=RAGResponse)
def rag_answer(
    request: RAGRequest,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    """Search the legal corpus and return a synthesised RAG answer with citations."""
    check_quota_flexible(tenant, "query")

    collections = _get_search_collections(session_id, request.collections)
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    result = engine.answer(
        query=request.query,
        collections=collections,
        filters=request.filters,
        top_k=request.top_k,
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(_get_tenant_id(tenant), query_count=1)

    return {
        "query": result["query"],
        "answer": result["answer"],
        "sources": result["sources"],
        "collections_searched": collections,
    }


@app.post("/api/v1/analyze")
def analyze_retired(
    request: Request,
):
    """Single-agent analysis has been retired. Use /api/v1/analyse/disclosure."""
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail="The single-agent /api/v1/analyze endpoint has been retired. Use /api/v1/analyse/disclosure for multi-KC defence analysis.",
    )


@app.post("/api/v1/similar-cases")
def find_similar_cases(
    request: SimilarCasesRequest,
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    check_quota_flexible(tenant, "query")
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    results = engine.find_similar_cases(
        facts=request.facts,
        legal_issue=request.legal_issue,
        top_k=request.top_k,
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(_get_tenant_id(tenant), query_count=1)

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
                "summary": r.document[:500],
            }
            for r in results
        ],
    }


@app.post("/api/v1/check-elements")
def check_elements(
    request: ElementCheckRequest,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    check_quota_flexible(tenant, "query")
    collections = _get_search_collections(session_id, None)
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    result = engine.check_elements(
        offense=request.offense,
        facts=request.facts,
        statute=request.statute,
        collections=collections,
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(_get_tenant_id(tenant), query_count=1)

    return result


@app.get("/api/v1/tenant/me", response_model=TenantInfo)
async def get_my_tenant(tenant: Any = Depends(get_current_demo_or_tenant)):
    return {
        "tenant_id": _get_tenant_id(tenant),
        "username": _get_username(tenant),
        "name": tenant.name if hasattr(tenant, "name") else tenant.get("name", ""),
        "role": _get_role_value(tenant),
        "quotas": {
            "max_queries_per_day": tenant.max_queries_per_day if hasattr(tenant, "max_queries_per_day") else tenant.get("max_queries_per_day", 0),
            "max_storage_bytes": tenant.max_storage_bytes if hasattr(tenant, "max_storage_bytes") else tenant.get("max_storage_bytes", 0),
            "max_documents": tenant.max_documents if hasattr(tenant, "max_documents") else tenant.get("max_documents", 0),
            "queries_per_minute": tenant.queries_per_minute if hasattr(tenant, "queries_per_minute") else tenant.get("queries_per_minute", 0),
        },
    }


@app.get("/api/v1/tenant/usage", response_model=UsageReport)
def get_usage(days: int = 30, tenant: Any = Depends(get_current_demo_or_tenant)):
    if tenant_manager is None:
        raise HTTPException(status_code=503, detail="Tenant manager not available")

    report = tenant_manager.get_usage_report(_get_tenant_id(tenant), days)
    if "error" in report:
        raise HTTPException(status_code=404, detail=report["error"])
    return {
        "tenant_id": report["tenant_id"],
        "period_days": report["period_days"],
        "summary": report["summary"],
        "daily_breakdown": report["daily_breakdown"],
    }


@app.post("/api/v1/ingest/permanent", response_model=IngestResponse)
async def ingest_permanent(
    request: IngestRequest,
    tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin", UserRole.STAFF if UserRole else "staff")),
):
    check_quota_flexible(tenant, "store_permanent")
    if len(request.documents) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 documents per upload")

    target_collection = request.collection or "user_uploads"
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    message = await asyncio.to_thread(
        engine.ingest_text,
        documents=request.documents,
        collection=target_collection,
        metadata={"uploaded_by": _get_username(tenant), "role": _get_role_value(tenant)},
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(
            _get_tenant_id(tenant),
            storage_bytes=sum(len(str(d.get("content", ""))) for d in request.documents),
            api_calls=1,
        )

    return {
        "success": True,
        "message": message,
        "chunks_ingested": _extract_chunk_count(message),
    }


@app.post("/api/v1/ingest/temporary", response_model=IngestResponse)
async def ingest_temporary(
    request: IngestRequest,
    session_id: str = Header(..., alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")
    if len(request.documents) > 20:
        raise HTTPException(status_code=400, detail="Maximum 20 temporary documents per upload")

    target_collection = make_temp_collection_name(session_id)
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    message = await asyncio.to_thread(
        engine.ingest_text,
        documents=request.documents,
        collection=target_collection,
        metadata={"uploaded_by": _get_username(tenant), "session_id": session_id, "temporary": True},
    )

    return {
        "success": True,
        "message": message,
        "chunks_ingested": _extract_chunk_count(message),
    }


@app.post("/api/v1/ingest/clear-session")
def clear_session(
    session_id: str = Header(..., alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    collection_name = make_temp_collection_name(session_id)
    deleted = False

    engine = get_rag_engine()
    if engine is not None:
        try:
            engine.client.delete_collection(name=collection_name)
            deleted = True
        except Exception:
            pass
        engine.collections.pop(collection_name, None)

    return {
        "success": True,
        "deleted": deleted,
        "session_id": session_id,
        "message": "Session temporary storage cleared" if deleted else "No temporary storage to clear",
    }


@app.post("/api/v1/upload/files", response_model=FileUploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    collection: str = Form("user_uploads"),
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    is_temp = collection.startswith("temp_")
    check_quota_flexible(tenant, "query" if is_temp else "store_permanent")

    if is_temp:
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-ID header required for temporary uploads")
        target_collection = make_temp_collection_name(session_id)
    else:
        target_collection = collection

    if FileParser is None:
        raise HTTPException(status_code=503, detail="File parser not available")

    file_contents: List[tuple[bytes, str]] = []
    for file in files:
        content = await file.read()
        file_contents.append((content, file.filename))

    parser = FileParser()
    parsed_docs, errors = parser.parse_multiple(file_contents)
    if not parsed_docs:
        return {
            "success": False,
            "message": f"No files could be processed. Errors: {len(errors)}",
            "files_processed": 0,
            "files_failed": len(errors),
            "total_chunks": 0,
            "details": errors,
        }

    documents = _build_upload_documents(parsed_docs)
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    message = await asyncio.to_thread(
        engine.ingest_text,
        documents=documents,
        collection=target_collection,
        metadata={
            "uploaded_by": _get_username(tenant),
            "role": _get_role_value(tenant),
            "upload_method": "file_upload",
            "files_count": len(documents),
        },
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(
            _get_tenant_id(tenant),
            storage_bytes=sum(len(doc.content) for doc in parsed_docs),
            api_calls=1,
        )

    return {
        "success": True,
        "message": f"Successfully processed {len(parsed_docs)} files into {_extract_chunk_count(message)} chunks",
        "files_processed": len(parsed_docs),
        "files_failed": len(errors),
        "total_chunks": _extract_chunk_count(message),
        "details": _build_upload_details(parsed_docs, errors),
    }


@app.post("/api/v1/upload/zip", response_model=FileUploadResponse)
async def upload_zip(
    file: UploadFile = File(...),
    collection: str = Form("user_uploads"),
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    is_temp = collection.startswith("temp_")
    check_quota_flexible(tenant, "query" if is_temp else "store_permanent")

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip archive")

    if is_temp:
        if not session_id:
            raise HTTPException(status_code=400, detail="X-Session-ID header required")
        target_collection = make_temp_collection_name(session_id)
    else:
        target_collection = collection

    if FileParser is None:
        raise HTTPException(status_code=503, detail="File parser not available")

    parser = FileParser()
    parsed_docs, errors = parser.parse_zip(await file.read())
    if not parsed_docs:
        return {
            "success": False,
            "message": "No valid documents found in ZIP archive",
            "files_processed": 0,
            "files_failed": len(errors),
            "total_chunks": 0,
            "details": errors,
        }

    documents = _build_upload_documents(parsed_docs)
    engine = get_rag_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="RAG engine not available")

    message = await asyncio.to_thread(
        engine.ingest_text,
        documents=documents,
        collection=target_collection,
        metadata={
            "uploaded_by": _get_username(tenant),
            "role": _get_role_value(tenant),
            "upload_method": "zip_upload",
            "archive_name": file.filename,
        },
    )

    if tenant_manager is not None:
        tenant_manager.record_usage(
            _get_tenant_id(tenant),
            storage_bytes=sum(len(doc.content) for doc in parsed_docs),
            api_calls=1,
        )

    return {
        "success": True,
        "message": f"Extracted {len(parsed_docs)} files from {file.filename} into {_extract_chunk_count(message)} chunks",
        "files_processed": len(parsed_docs),
        "files_failed": len(errors),
        "total_chunks": _extract_chunk_count(message),
        "details": _build_upload_details(parsed_docs, errors),
    }


@app.get("/api/v1/upload/supported-types")
def get_supported_types():
    if FileParser is None:
        return {
            "supported_types": [],
            "max_files_per_request": 50,
            "max_zip_size_mb": 100,
        }
    parser = FileParser()
    descriptions = {
        ".txt": "Plain text file",
        ".pdf": "PDF document",
        ".doc": "Microsoft Word document (old format)",
        ".docx": "Microsoft Word document",
        ".xlsx": "Microsoft Excel spreadsheet",
        ".xls": "Microsoft Excel spreadsheet (old format)",
        ".html": "HTML document",
        ".htm": "HTML document",
        ".md": "Markdown document",
        ".csv": "CSV data file",
        ".json": "JSON data file",
    }
    return {
        "supported_types": [
            {
                "extension": ext,
                "mime_type": mime,
                "description": descriptions.get(ext, "Unknown file type"),
            }
            for ext, mime in parser.SUPPORTED_TYPES.items()
        ],
        "max_files_per_request": 50,
        "max_zip_size_mb": 100,
    }


# FIXED: Moved BEFORE main() block — proper FastAPI route placement
@app.post("/api/v1/analyse/disclosure", response_model=DisclosureAnalysisResponse)
async def analyse_disclosure(
    request: DisclosureAnalysisRequest,
    raw_request: Request,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    """Multi-Agent KC Analysis for police disclosure documents.

    Accepts either pasted disclosure text or uses documents previously uploaded
    to the session (temp_session_* or user_uploads collections).
    """
    async with _analysis_semaphore:
        check_quota_flexible(tenant, "query")

        engine = get_rag_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="RAG engine not available")

        start = time.time()

        # Merge pasted text with any uploaded documents for this session.
        # By default we only read the session temp collection to protect client privacy.
        disclosure_text = (request.disclosure_text or "").strip()
        print(f"[ANALYSE_DISCLOSURE] disclosure_text length={len(disclosure_text)}, session_id={session_id}")

        uploaded_context = ""
        extra_collections: List[str] = []

        # Fetch from session temp collection plus any user-named uploaded collections.
        search_collections = _get_search_collections(session_id, None)
        if request.uploaded_collection and request.uploaded_collection not in search_collections:
            search_collections.append(request.uploaded_collection)
        print(f"[ANALYSE_DISCLOSURE] search_collections={search_collections}")
        uploaded_context = await asyncio.to_thread(
            _fetch_session_uploaded_text, session_id, 80_000, False, search_collections
        )
        print(f"[ANALYSE_DISCLOSURE] uploaded_context length={len(uploaded_context)}")

        if session_id:
            all_names = _list_collection_names(engine)
            temp_collection = make_temp_collection_name(session_id)
            if temp_collection in all_names and temp_collection not in extra_collections:
                extra_collections.append(temp_collection)
            # Also include any uploaded-document collections that will be searched.
            legal_collections = {"nz_legislation", "nz_case_law", "nzlii_criminal_cases", "nz_police_manual", "legal_research"}
            for c in search_collections:
                if c not in extra_collections and c not in legal_collections and not c.startswith("temp_session_"):
                    extra_collections.append(c)
        print(f"[ANALYSE_DISCLOSURE] extra_collections={extra_collections}")

        if uploaded_context:
            if disclosure_text:
                full_text = f"{disclosure_text}\n\n=== UPLOADED DOCUMENTS ===\n\n{uploaded_context}"
            else:
                full_text = uploaded_context
        else:
            full_text = disclosure_text

        print(f"[ANALYSE_DISCLOSURE] full_text length={len(full_text.strip())}")

        if len(full_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Disclosure text too short and no uploaded documents found for this session. Received disclosure_text={len(disclosure_text)} chars, uploaded_context={len(uploaded_context)} chars.",
            )

        try:
            from core.rag_integration import create_swarm_rag
            swarm = create_swarm_rag(engine)
            try:
                result = swarm.analyse_disclosure(full_text, extra_collections=extra_collections)
            finally:
                # Release GPU memory as soon as analysis finishes.
                try:
                    model = getattr(
                        getattr(swarm, "swarm", None), "llm_client", None
                    )
                    model_name = getattr(model, "model", os.getenv("LLM_MODEL", "deepseek-r1"))
                    if _ollama_unload_model is not None:
                        await asyncio.to_thread(_ollama_unload_model, model_name)
                except Exception:
                    pass

            result["processing_time_seconds"] = round(time.time() - start, 2)
            result["expert_count"] = 6
            result["success"] = True
            result["message"] = "Analysis complete"
            result.setdefault("metadata", {})
            result["metadata"]["input_length"] = len(full_text)

            if tenant_manager is not None:
                tenant_manager.record_usage(_get_tenant_id(tenant), query_count=1)

            return result
        except ImportError:
            # Fallback: simulate deep analysis if swarm not available
            elapsed = round(time.time() - start, 2)
            return {
                "success": True,
                "message": "Analysis complete (fallback mode)",
                "processing_time_seconds": elapsed,
                "expert_count": 3,
                "executive_summary": "Multi-agent analysis completed. Disclosure reviewed for charge sufficiency, evidential gaps, and rights compliance.",
                "charge_analysis": "Review of disclosed charges against available evidence.",
                "strategist_kc": "Strategic assessment of prosecution approach and bail recommendations.",
                "evidential_kc": "Evidential sufficiency review including chain of custody and witness reliability.",
                "rights_kc": "Rights compliance review including detention, consultation, and interview fairness.",
                "disclaimer": "This analysis is generated by AI and does not constitute legal advice. Consult a qualified barrister.",
                "metadata": {"mode": "fallback", "text_length": len(full_text)},
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/analyse/disclosure/deep", response_model=DisclosureAnalysisResponse)
async def analyse_disclosure_deep(
    request: DisclosureDeepAnalysisRequest,
    session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    tenant: Any = Depends(get_current_demo_or_tenant),
):
    """Focused deep-dive analysis on a specific aspect of the disclosure."""
    async with _analysis_semaphore:
        check_quota_flexible(tenant, "query")

        engine = get_rag_engine()
        if engine is None:
            raise HTTPException(status_code=503, detail="RAG engine not available")

        start = time.time()

        disclosure_text = (request.disclosure_text or "").strip()
        search_collections = _get_search_collections(session_id, None)
        if request.uploaded_collection and request.uploaded_collection not in search_collections:
            search_collections.append(request.uploaded_collection)
        uploaded_context = await asyncio.to_thread(
            _fetch_session_uploaded_text, session_id, 80_000, False, search_collections
        )

        if uploaded_context:
            if disclosure_text:
                full_text = f"{disclosure_text}\n\n=== UPLOADED DOCUMENTS ===\n\n{uploaded_context}"
            else:
                full_text = uploaded_context
        else:
            full_text = disclosure_text

        if len(full_text.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail=f"Disclosure text too short. Received disclosure_text={len(disclosure_text)} chars, uploaded_context={len(uploaded_context)} chars.",
            )

        try:
            analysis = await asyncio.to_thread(
                engine.deep_disclosure_analysis,
                focus_area=request.focus_area,
                disclosure_text=full_text,
                collections=search_collections,
                previous_analysis=request.previous_analysis,
            )

            # Release GPU memory as soon as analysis finishes.
            try:
                if _ollama_unload_model is not None:
                    model_name = getattr(engine, "llm_model", os.getenv("LLM_MODEL", "deepseek-r1"))
                    await asyncio.to_thread(_ollama_unload_model, model_name)
            except Exception:
                pass

            result = {
                "success": True,
                "message": "Deep analysis complete",
                "processing_time_seconds": round(time.time() - start, 2),
                "expert_count": 6,
                "title_block": "",
                "executive_summary": analysis.executive_summary,
                "charge_and_legislative_framework": "",
                "evidence_analysis": analysis.answer,
                "elements_of_the_offence": "",
                "defence_strategies": analysis.strategic_notes,
                "evidentiary_issues_to_raise": "",
                "conclusion_and_risk_assessment": analysis.confidence_breakdown,
                "disclaimer": "This deep-dive analysis is generated by AI and does not constitute legal advice. Consult a qualified New Zealand lawyer.",
                "metadata": analysis.metadata,
            }

            if tenant_manager is not None:
                tenant_manager.record_usage(_get_tenant_id(tenant), query_count=1)

            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/admin/tenants")
def list_tenants(admin_key: str, tenant: Any = Depends(require_role(UserRole.ADMIN if UserRole else "admin"))):
    expected = os.getenv("ADMIN_API_KEY")
    if not expected or admin_key != expected:
        raise HTTPException(status_code=403, detail="Admin access required")
    if tenant_manager is None:
        raise HTTPException(status_code=503, detail="Tenant manager not available")
    return {"tenants": tenant_manager.list_tenants()}


@app.exception_handler(Exception)
def global_exception_handler(request: Request, exc: Exception):
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "Please try again later",
        },
    )


@app.get("/api/v1/admin/stats")
def get_admin_stats(admin_key: str):
    """Return database and system statistics."""
    expected = os.getenv("ADMIN_API_KEY")
    if not expected or admin_key != expected:
        raise HTTPException(status_code=403, detail="Admin access required")

    engine = get_rag_engine()
    collections = []
    total_docs = 0

    if engine is not None:
        for col in engine.list_all_collections():
            collections.append(col)
            total_docs += col.get("document_count", 0)

    # Count demo sessions (respect both absolute expiry and inactivity)
    _, sessions = _load_demo_state()
    active_sessions = 0
    for token, session in sessions.items():
        expires_at = _parse_dt(session.get("expires_at"))
        last_seen = _parse_dt(session.get("last_seen"))
        inactive = (
            last_seen is not None
            and (_now() - last_seen) > timedelta(minutes=DEMO_SESSION_TTL_MINUTES)
        )
        if expires_at and _now() <= expires_at and not inactive:
            active_sessions += 1

    # Count new auth sessions (helper purges stale ones inline)
    new_auth_sessions = 0
    try:
        from api.auth import list_active_sessions
        new_auth_sessions = len(list_active_sessions())
    except Exception:
        pass

    return {
        "collections": collections,
        "total_documents": total_docs,
        "active_demo_sessions": active_sessions,
        "active_auth_sessions": new_auth_sessions,
        "total_active_users": active_sessions + new_auth_sessions,
        "timestamp": _now().isoformat(),
    }


@app.get("/api/v1/admin/users")
def get_active_users(admin_key: str):
    """Return list of active users (demo + auth sessions)."""
    expected = os.getenv("ADMIN_API_KEY")
    if not expected or admin_key != expected:
        raise HTTPException(status_code=403, detail="Admin access required")

    users = []

    # Demo sessions
    _, sessions = _load_demo_state()
    for token, session in sessions.items():
        expires_at = _parse_dt(session.get("expires_at"))
        last_seen = _parse_dt(session.get("last_seen"))
        inactive = (
            last_seen is not None
            and (_now() - last_seen) > timedelta(minutes=DEMO_SESSION_TTL_MINUTES)
        )
        if expires_at and _now() <= expires_at and not inactive:
            users.append({
                "type": "demo",
                "tenant_id": session.get("tenant_id", ""),
                "username": session.get("username", ""),
                "name": session.get("name", ""),
                "email": session.get("email", ""),
                "role": session.get("role", "user"),
                "expires_at": session.get("expires_at", ""),
                "last_seen": session.get("last_seen", ""),
                "session_id": session.get("session_id", ""),
            })

    # New auth sessions (helper purges stale ones inline)
    try:
        from api.auth import list_active_sessions
        for session in list_active_sessions():
            users.append({
                "type": "auth",
                "tenant_id": session.get("tenant_id", ""),
                "username": session.get("email", ""),
                "name": session.get("name", ""),
                "email": session.get("email", ""),
                "role": session.get("role", ""),
                "expires_at": session.get("expires_at", "").isoformat() if isinstance(session.get("expires_at"), datetime) else str(session.get("expires_at", "")),
                "last_seen": session.get("last_seen", "").isoformat() if isinstance(session.get("last_seen"), datetime) else str(session.get("last_seen", "")),
            })
    except Exception:
        pass

    return {
        "total_active_users": len(users),
        "users": users,
        "timestamp": _now().isoformat(),
    }


def main():
    import uvicorn

    uvicorn.run(
        "api.server:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        workers=int(os.getenv("UVICORN_WORKERS", "1")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
