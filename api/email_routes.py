"""Admin endpoints for the email disclosure bridge."""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from services.email_client import ImapClient, SmtpClient
from services.email_config import EmailConfig, get_email_config
from services.email_job_store import EmailJobStore, JobStatus
from services.email_poller import EmailPoller
from services.email_processor import EmailProcessor

router = APIRouter(prefix="/api/v1/email", tags=["email"])


def _get_current_demo_or_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
):
    """Lazily import auth dependency to avoid circular imports with api.server."""
    from api.server import get_current_demo_or_tenant as _server_auth

    return _server_auth(credentials)


_store_cache: Optional[EmailJobStore] = None


def _get_store() -> EmailJobStore:
    """Return the cached EmailJobStore, creating it on first call."""
    global _store_cache
    if _store_cache is None:
        db_path = os.path.join(
            os.getenv("TENANT_DATA_PATH", "./tenant_data"), "email_jobs.db"
        )
        _store_cache = EmailJobStore(db_path)
    return _store_cache


async def _check_imap(cfg: EmailConfig) -> tuple[bool, Optional[str]]:
    """Check IMAP connectivity by connecting and disconnecting."""
    try:
        def _connect():
            client = ImapClient(cfg)
            client.connect()
            client.disconnect()
        await asyncio.to_thread(_connect)
        return True, None
    except Exception as exc:
        return False, str(exc)


async def _check_smtp(cfg: EmailConfig) -> tuple[bool, Optional[str]]:
    """Check SMTP connectivity by delegating to SmtpClient."""
    try:
        await asyncio.to_thread(SmtpClient(cfg).check_connection)
        return True, None
    except Exception as exc:
        return False, str(exc)


@router.get("/health")
async def email_health(
    tenant: Any = Depends(_get_current_demo_or_tenant),
) -> dict:
    """Return email bridge health status; redact host details when disabled."""
    cfg = get_email_config()
    if not cfg.enabled:
        return {"enabled": False}
    result = {
        "enabled": True,
        "imap_host": cfg.imap_host,
        "smtp_host": cfg.smtp_host,
        "poll_interval_seconds": cfg.poll_interval_seconds,
    }
    imap_ok, imap_err = await _check_imap(cfg)
    smtp_ok, smtp_err = await _check_smtp(cfg)
    result["imap_ok"] = imap_ok
    result["smtp_ok"] = smtp_ok
    if imap_err:
        result["imap_error"] = imap_err
    if smtp_err:
        result["smtp_error"] = smtp_err
    return result


@router.post("/fetch")
async def email_fetch(
    tenant: Any = Depends(_get_current_demo_or_tenant),
) -> dict:
    """Trigger a single poll of the configured email account."""
    cfg = get_email_config()
    if not cfg.enabled:
        raise HTTPException(status_code=400, detail="Email bridge not enabled")
    store = _get_store()
    from api.server import _analysis_semaphore

    processor = EmailProcessor(cfg, store, _analysis_semaphore)
    poller = EmailPoller(cfg, processor)
    await poller.poll_once()
    return {"status": "ok"}


@router.get("/jobs")
async def list_jobs(
    status: Optional[str] = Query(None),
    days: int = Query(7, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tenant: Any = Depends(_get_current_demo_or_tenant),
) -> dict:
    """List email jobs, optionally filtered by status and recency."""
    store = _get_store()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    job_status = None
    if status:
        try:
            job_status = JobStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid status: {status}. Valid values: {', '.join(s.value for s in JobStatus)}",
            )
    jobs = store.list_jobs(status=job_status, since=since, limit=limit, offset=offset)
    return {
        "jobs": [
            {
                "id": j.id,
                "message_id": j.message_id,
                "sender": j.sender,
                "subject": j.subject,
                "received_at": j.received_at.isoformat(),
                "attachment_count": j.attachment_count,
                "status": j.status.value,
                "retry_count": j.retry_count,
                "result_path": j.result_path,
                "error_message": j.error_message,
                "updated_at": j.updated_at.isoformat(),
            }
            for j in jobs
        ]
    }


@router.get("/jobs/{job_id}")
async def get_job(
    job_id: str,
    tenant: Any = Depends(_get_current_demo_or_tenant),
) -> dict:
    """Return a single email job by ID."""
    store = _get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "message_id": job.message_id,
        "sender": job.sender,
        "subject": job.subject,
        "received_at": job.received_at.isoformat(),
        "attachment_count": job.attachment_count,
        "status": job.status.value,
        "retry_count": job.retry_count,
        "result_path": job.result_path,
        "error_message": job.error_message,
        "updated_at": job.updated_at.isoformat(),
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(
    job_id: str,
    tenant: Any = Depends(_get_current_demo_or_tenant),
) -> dict:
    """Retry a failed or quarantined email job."""
    cfg = get_email_config()
    if not cfg.enabled:
        raise HTTPException(status_code=400, detail="Email bridge not enabled")
    store = _get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in (JobStatus.FAILED, JobStatus.QUARANTINED):
        raise HTTPException(
            status_code=400,
            detail=f"Job status {job.status.value} cannot be retried",
        )
    if not job.raw_email_bytes:
        raise HTTPException(
            status_code=400, detail="Original email not available for retry"
        )
    from api.server import _analysis_semaphore

    processor = EmailProcessor(cfg, store, _analysis_semaphore)
    result = await processor.retry_job(job_id)
    return {"success": result.success, "error": result.error_message}


@router.get("/jobs/{job_id}/report")
async def get_job_report(
    job_id: str,
    tenant: Any = Depends(_get_current_demo_or_tenant),
):
    """Download the generated report for a completed email job."""
    store = _get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.result_path or not os.path.exists(job.result_path):
        raise HTTPException(status_code=404, detail="Report not found")
    media_type = "application/octet-stream"
    if job.result_path.endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif job.result_path.endswith(".pdf"):
        media_type = "application/pdf"
    elif job.result_path.endswith(".txt"):
        media_type = "text/plain"
    return FileResponse(
        job.result_path,
        media_type=media_type,
        filename=os.path.basename(job.result_path),
    )


@router.get("/metrics")
async def email_metrics(
    tenant: Any = Depends(_get_current_demo_or_tenant),
) -> dict:
    """Return aggregate counts of email jobs by status."""
    store = _get_store()
    return {"counts": store.get_counts()}
