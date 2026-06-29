from fastapi import APIRouter, HTTPException, Response, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import uuid
import hashlib
import secrets

router = APIRouter(prefix="/auth", tags=["auth"])

_sessions = {}

# Session inactivity timeout (default 20 minutes)
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "20"))


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    tenant_id: str
    role: str


def _create_token(tenant_id: str, role: str = "user") -> str:
    payload = f"{tenant_id}:{role}:{datetime.utcnow().isoformat()}:{secrets.token_hex(16)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def create_session(tenant_id: str, role: str = "user", email: str = "", name: str = "") -> str:
    """Create a tracked session and return its token. Used by /auth/login and staff login."""
    token = _create_token(tenant_id, role)
    now = datetime.utcnow()
    expires_at = now + timedelta(minutes=SESSION_TTL_MINUTES)
    _sessions[token] = {
        "tenant_id": tenant_id,
        "email": email,
        "name": name,
        "role": role,
        "created_at": now,
        "expires_at": expires_at,
        "last_seen": now,
    }
    return token


def _is_session_active(session: dict) -> bool:
    """Check whether a session is still active based on absolute expiry and inactivity."""
    now = datetime.utcnow()
    if session.get("expires_at") and session["expires_at"] < now:
        return False
    last_seen = session.get("last_seen")
    if last_seen and (now - last_seen) > timedelta(minutes=SESSION_TTL_MINUTES):
        return False
    return True


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response):
    tenant_id = f"demo_{uuid.uuid4().hex[:12]}"
    token = create_session(tenant_id, role="user", email=req.email)
    expires_in = SESSION_TTL_MINUTES * 60

    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        max_age=expires_in,
        samesite="lax",
    )

    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        tenant_id=tenant_id,
        role="user",
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get("session_token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token in _sessions:
        del _sessions[token]
    response.delete_cookie("session_token")
    return {"ok": True}


def get_current_tenant(token: str) -> dict:
    if token not in _sessions:
        return None  # Token not found - let caller handle fallback
    session = _sessions[token]
    if not _is_session_active(session):
        del _sessions[token]
        return None  # Token expired or inactive - let caller handle fallback
    # Update last_seen on every successful auth check
    session["last_seen"] = datetime.utcnow()
    return session


def list_active_sessions() -> list:
    """Return all currently active sessions, purging stale ones inline."""
    now = datetime.utcnow()
    active = []
    stale_tokens = []
    for token, session in _sessions.items():
        if _is_session_active(session):
            active.append({"token": token, **session})
        else:
            stale_tokens.append(token)
    for token in stale_tokens:
        del _sessions[token]
    return active
