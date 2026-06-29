> I'm using the writing-plans skill to create the implementation plan.

# AEGIS Email Disclosure Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an email bridge so anyone can email a disclosure to a configured AEGIS inbox and receive a DOCX analysis brief back automatically.

**Architecture:** A FastAPI lifespan poller fetches unseen IMAP messages, an `email_processor` parses/ingests/analyses them by reusing the existing AEGIS pipeline, and an SMTP client sends back the report. Job state lives in SQLite; admin endpoints and a Streamlit page provide observability and manual controls.

**Tech Stack:** Python stdlib (`imaplib`, `smtplib`, `email`, `sqlite3`), existing AEGIS components (`FileParser`, `AgentSwarm`, `ReportExport`, `ChromaDB`), FastAPI, Streamlit.

---

## File Structure

| File | Purpose |
|------|---------|
| `services/__init__.py` | Package marker. |
| `services/email_config.py` | Env-var config, validation, defaults. |
| `services/email_client.py` | IMAP + SMTP thin wrappers with SSL/TLS. |
| `services/email_job_store.py` | SQLite schema and CRUD for email jobs. |
| `services/email_processor.py` | Parse email, extract attachments, run AEGIS analysis, build report, reply. |
| `services/email_poller.py` | Background asyncio polling loop. |
| `api/email_routes.py` | FastAPI endpoints for health, jobs, metrics, fetch, retry. |
| `api/server.py` | Register lifespan poller and include email router. |
| `web/streamlit_app.py` | New "Email Inbox" page for monitoring/retry. |
| `tests/services/test_email_config.py` | Config validation tests. |
| `tests/services/test_email_job_store.py` | Job store tests. |
| `tests/services/test_email_client.py` | Mocked IMAP/SMTP tests. |
| `tests/services/test_email_processor.py` | End-to-end processor test with mocked RAG. |
| `tests/services/test_email_poller.py` | Poller loop tests. |
| `tests/api/test_email_routes.py` | API endpoint tests. |
| `.env.example` | New email-related env vars. |

---

### Task 1: Create `services` package and config module

**Files:**
- Create: `services/__init__.py`
- Create: `services/email_config.py`
- Test: `tests/services/test_email_config.py`

- [ ] **Step 1: Write the failing config test**

Create `tests/services/test_email_config.py`:

```python
import os
import pytest
from services.email_config import EmailConfig, get_email_config


class TestEmailConfig:
    def test_config_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("AEGIS_EMAIL_POLLER_ENABLED", raising=False)
        cfg = get_email_config()
        assert cfg.enabled is False

    def test_config_enabled_requires_imap_smtp(self, monkeypatch):
        monkeypatch.setenv("AEGIS_EMAIL_POLLER_ENABLED", "true")
        monkeypatch.setenv("AEGIS_EMAIL_IMAP_HOST", "imap.example.com")
        monkeypatch.setenv("AEGIS_EMAIL_IMAP_USERNAME", "user")
        monkeypatch.setenv("AEGIS_EMAIL_IMAP_PASSWORD", "pass")
        monkeypatch.setenv("AEGIS_EMAIL_SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("AEGIS_EMAIL_SMTP_USERNAME", "user")
        monkeypatch.setenv("AEGIS_EMAIL_SMTP_PASSWORD", "pass")
        cfg = get_email_config()
        assert cfg.enabled is True
        assert cfg.imap_host == "imap.example.com"
        assert cfg.imap_port == 993
        assert cfg.imap_use_ssl is True
        assert cfg.smtp_port == 587
        assert cfg.smtp_use_tls is True
        assert cfg.poll_interval_seconds == 60
        assert cfg.max_retries == 3
        assert cfg.sender_daily_limit == 10
        assert cfg.max_attachment_bytes == 25 * 1024 * 1024
        assert cfg.dry_run is False

    def test_config_missing_required_raises(self, monkeypatch):
        monkeypatch.setenv("AEGIS_EMAIL_POLLER_ENABLED", "true")
        monkeypatch.delenv("AEGIS_EMAIL_IMAP_HOST", raising=False)
        with pytest.raises(ValueError):
            get_email_config()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'services.email_config'`.

- [ ] **Step 3: Implement `services/__init__.py` and `services/email_config.py`**

Create `services/__init__.py`:

```python
# services package
```

Create `services/email_config.py`:

```python
"""Email bridge configuration."""
from dataclasses import dataclass
import os
from typing import Optional


@dataclass(frozen=True)
class EmailConfig:
    enabled: bool
    imap_host: Optional[str]
    imap_port: int
    imap_use_ssl: bool
    imap_username: Optional[str]
    imap_password: Optional[str]
    smtp_host: Optional[str]
    smtp_port: int
    smtp_use_tls: bool
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    inbox_name: str
    poll_interval_seconds: int
    max_retries: int
    sender_daily_limit: int
    max_attachment_bytes: int
    dry_run: bool
    system_tenant_id: str


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    return int(value) if value else default


def get_email_config() -> EmailConfig:
    enabled = _env_bool("AEGIS_EMAIL_POLLER_ENABLED")

    cfg = EmailConfig(
        enabled=enabled,
        imap_host=os.getenv("AEGIS_EMAIL_IMAP_HOST") or None,
        imap_port=_env_int("AEGIS_EMAIL_IMAP_PORT", 993),
        imap_use_ssl=_env_bool("AEGIS_EMAIL_IMAP_USE_SSL", True),
        imap_username=os.getenv("AEGIS_EMAIL_IMAP_USERNAME") or None,
        imap_password=os.getenv("AEGIS_EMAIL_IMAP_PASSWORD") or None,
        smtp_host=os.getenv("AEGIS_EMAIL_SMTP_HOST") or None,
        smtp_port=_env_int("AEGIS_EMAIL_SMTP_PORT", 587),
        smtp_use_tls=_env_bool("AEGIS_EMAIL_SMTP_USE_TLS", True),
        smtp_username=os.getenv("AEGIS_EMAIL_SMTP_USERNAME") or None,
        smtp_password=os.getenv("AEGIS_EMAIL_SMTP_PASSWORD") or None,
        inbox_name=os.getenv("AEGIS_EMAIL_INBOX_NAME") or "INBOX",
        poll_interval_seconds=_env_int("AEGIS_EMAIL_POLL_INTERVAL_SECONDS", 60),
        max_retries=_env_int("AEGIS_EMAIL_MAX_RETRIES", 3),
        sender_daily_limit=_env_int("AEGIS_EMAIL_SENDER_DAILY_LIMIT", 10),
        max_attachment_bytes=_env_int("AEGIS_EMAIL_MAX_ATTACHMENT_BYTES", 25 * 1024 * 1024),
        dry_run=_env_bool("AEGIS_EMAIL_DRY_RUN"),
        system_tenant_id=os.getenv("AEGIS_EMAIL_SYSTEM_TENANT_ID") or "system_email",
    )

    if cfg.enabled:
        required = [
            cfg.imap_host,
            cfg.imap_username,
            cfg.imap_password,
            cfg.smtp_host,
            cfg.smtp_username,
            cfg.smtp_password,
        ]
        if any(v is None or v == "" for v in required):
            raise ValueError(
                "AEGIS_EMAIL_POLLER_ENABLED is true but one or more required "
                "IMAP/SMTP settings are missing."
            )
    return cfg
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_config.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/megab/aegis && git add services/__init__.py services/email_config.py tests/services/test_email_config.py
git commit -m "feat(email): add email bridge configuration module"
```

---

### Task 2: Create SQLite job store

**Files:**
- Create: `services/email_job_store.py`
- Test: `tests/services/test_email_job_store.py`

- [ ] **Step 1: Write the failing job-store test**

Create `tests/services/test_email_job_store.py`:

```python
import os
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from services.email_job_store import EmailJobStore, JobStatus


class TestEmailJobStore:
    @pytest.fixture
    def store(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = EmailJobStore(path)
        yield store
        os.unlink(path)

    def test_create_and_get(self, store):
        job = store.create_job(
            message_id="<msg-1@example.com>",
            sender="client@example.com",
            subject="Disclosure",
            attachment_count=2,
            raw_email_bytes=b"raw-email",
        )
        assert job.status == JobStatus.RECEIVED
        fetched = store.get_job(job.id)
        assert fetched.message_id == "<msg-1@example.com>"
        assert fetched.sender == "client@example.com"
        assert fetched.raw_email_bytes == b"raw-email"

    def test_dedupe_by_message_id(self, store):
        job1 = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        job2 = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        assert job1.id == job2.id

    def test_update_status_and_list(self, store):
        job = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        store.update_status(job.id, JobStatus.COMPLETED, result_path="/tmp/x.docx")
        fetched = store.get_job(job.id)
        assert fetched.status == JobStatus.COMPLETED
        assert fetched.result_path == "/tmp/x.docx"
        jobs = store.list_jobs(status=JobStatus.COMPLETED)
        assert len(jobs) == 1

    def test_increment_retry(self, store):
        job = store.create_job("<msg-1@example.com>", "a@example.com", "X", 0, b"raw")
        store.increment_retry(job.id, "boom")
        fetched = store.get_job(job.id)
        assert fetched.retry_count == 1
        assert "boom" in fetched.error_message

    def test_counts_and_sender_limit(self, store):
        today = datetime.now(timezone.utc)
        store.create_job("<m1>", "a@example.com", "X", 0, b"raw")
        store.create_job("<m2>", "a@example.com", "X", 0, b"raw")
        store.create_job("<m3>", "b@example.com", "X", 0, b"raw")
        assert store.get_sender_count_since("a@example.com", today - timedelta(days=1)) == 2
        assert store.get_counts()["total"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_job_store.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `services/email_job_store.py`**

Create `services/email_job_store.py`:

```python
"""SQLite job store for email disclosure analysis jobs."""
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional


class JobStatus(str, Enum):
    RECEIVED = "received"
    PARSING = "parsing"
    ANALYSING = "analysing"
    COMPLETED = "completed"
    FAILED = "failed"
    QUARANTINED = "quarantined"


@dataclass
class EmailJob:
    id: str
    message_id: str
    sender: str
    subject: str
    received_at: datetime
    attachment_count: int
    status: JobStatus
    retry_count: int
    result_path: Optional[str]
    error_message: Optional[str]
    raw_email_bytes: Optional[bytes]
    updated_at: datetime


class EmailJobStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS email_jobs (
                    id TEXT PRIMARY KEY,
                    message_id TEXT UNIQUE NOT NULL,
                    sender TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    attachment_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    result_path TEXT,
                    error_message TEXT,
                    raw_email_bytes BLOB,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_jobs_status ON email_jobs(status)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_jobs_sender ON email_jobs(sender)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_email_jobs_received_at ON email_jobs(received_at)"
            )

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _row_to_job(self, row: sqlite3.Row) -> EmailJob:
        return EmailJob(
            id=row["id"],
            message_id=row["message_id"],
            sender=row["sender"],
            subject=row["subject"],
            received_at=datetime.fromisoformat(row["received_at"]),
            attachment_count=row["attachment_count"],
            status=JobStatus(row["status"]),
            retry_count=row["retry_count"],
            result_path=row["result_path"],
            error_message=row["error_message"],
            raw_email_bytes=row["raw_email_bytes"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def create_job(
        self,
        message_id: str,
        sender: str,
        subject: str,
        attachment_count: int,
        raw_email_bytes: bytes,
    ) -> EmailJob:
        existing = self.get_job_by_message_id(message_id)
        if existing:
            return existing
        now = self._now()
        job_id = str(uuid.uuid4())
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO email_jobs
                (id, message_id, sender, subject, received_at, attachment_count, status, retry_count, result_path, error_message, raw_email_bytes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    message_id,
                    sender,
                    subject,
                    now,
                    attachment_count,
                    JobStatus.RECEIVED.value,
                    0,
                    None,
                    None,
                    raw_email_bytes,
                    now,
                ),
            )
        return self.get_job(job_id)

    def get_job(self, job_id: str) -> Optional[EmailJob]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM email_jobs WHERE id = ?", (job_id,)).fetchone()
        return self._row_to_job(row) if row else None

    def get_job_by_message_id(self, message_id: str) -> Optional[EmailJob]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM email_jobs WHERE message_id = ?", (message_id,)
            ).fetchone()
        return self._row_to_job(row) if row else None

    def update_status(
        self,
        job_id: str,
        status: JobStatus,
        result_path: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE email_jobs
                SET status = ?, result_path = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (status.value, result_path, error_message, self._now(), job_id),
            )

    def increment_retry(self, job_id: str, error_message: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE email_jobs
                SET retry_count = retry_count + 1, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (error_message, self._now(), job_id),
            )

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EmailJob]:
        query = "SELECT * FROM email_jobs WHERE 1=1"
        params: List = []
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if since:
            query += " AND received_at >= ?"
            params.append(since.isoformat())
        query += " ORDER BY received_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_counts(self) -> dict:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM email_jobs GROUP BY status"
            ).fetchall()
        counts = {s.value: 0 for s in JobStatus}
        for row in rows:
            counts[row["status"]] = row["cnt"]
        counts["total"] = sum(counts.values())
        return counts

    def get_sender_count_since(self, sender: str, since: datetime) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM email_jobs WHERE sender = ? AND received_at >= ?",
                (sender, since.isoformat()),
            ).fetchone()
        return row["cnt"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_job_store.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/megab/aegis && git add services/email_job_store.py tests/services/test_email_job_store.py
git commit -m "feat(email): add SQLite job store for email analysis jobs"
```

---

### Task 3: Create IMAP + SMTP client

**Files:**
- Create: `services/email_client.py`
- Test: `tests/services/test_email_client.py`

- [ ] **Step 1: Write the failing email-client test**

Create `tests/services/test_email_client.py`:

```python
import io
from unittest.mock import MagicMock, patch
import pytest
from services.email_client import ImapClient, SmtpClient
from services.email_config import EmailConfig


class TestImapClient:
    @pytest.fixture
    def cfg(self):
        return EmailConfig(
            enabled=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_use_ssl=True,
            imap_username="user",
            imap_password="pass",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="user",
            smtp_password="pass",
            inbox_name="INBOX",
            poll_interval_seconds=60,
            max_retries=3,
            sender_daily_limit=10,
            max_attachment_bytes=25 * 1024 * 1024,
            dry_run=False,
            system_tenant_id="system_email",
        )

    @patch("services.email_client.imaplib")
    def test_fetch_unseen(self, mock_imaplib, cfg):
        mock_conn = MagicMock()
        mock_imaplib.IMAP4_SSL.return_value = mock_conn
        mock_conn.search.return_value = ("OK", [b"1 2"])
        mock_conn.fetch.side_effect = [
            ("OK", [(b"1", b"raw-email-1")]),
            ("OK", [(b"2", b"raw-email-2")]),
        ]
        client = ImapClient(cfg)
        client.connect()
        messages = client.fetch_unseen()
        assert len(messages) == 2
        assert messages[0] == b"raw-email-1"
        client.mark_seen(b"1")
        mock_conn.store.assert_called_once()


class TestSmtpClient:
    @pytest.fixture
    def cfg(self):
        return EmailConfig(
            enabled=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_use_ssl=True,
            imap_username="user",
            imap_password="pass",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="user",
            smtp_password="pass",
            inbox_name="INBOX",
            poll_interval_seconds=60,
            max_retries=3,
            sender_daily_limit=10,
            max_attachment_bytes=25 * 1024 * 1024,
            dry_run=False,
            system_tenant_id="system_email",
        )

    @patch("services.email_client.smtplib")
    def test_send_reply_with_attachment(self, mock_smtplib, cfg):
        mock_conn = MagicMock()
        mock_smtplib.SMTP.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_smtplib.SMTP.return_value.__exit__ = MagicMock(return_value=False)
        client = SmtpClient(cfg)
        client.send_reply(
            to_address="client@example.com",
            subject="RE: Disclosure",
            body="See attached.",
            attachment_bytes=b"docx-bytes",
            attachment_filename="report.docx",
        )
        mock_conn.send_message.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_client.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `services/email_client.py`**

Create `services/email_client.py`:

```python
"""IMAP/SMTP clients for the email bridge."""
import imaplib
import smtplib
from email import message_from_bytes
from email.message import EmailMessage
from email.utils import parseaddr
from typing import List, Tuple

from services.email_config import EmailConfig


class ImapClient:
    def __init__(self, config: EmailConfig):
        self.config = config
        self._conn = None

    def connect(self) -> None:
        if self.config.imap_use_ssl:
            self._conn = imaplib.IMAP4_SSL(
                self.config.imap_host, self.config.imap_port
            )
        else:
            self._conn = imaplib.IMAP4(self.config.imap_host, self.config.imap_port)
            try:
                self._conn.starttls()
            except Exception:
                pass
        self._conn.login(self.config.imap_username, self.config.imap_password)
        self._conn.select(self.config.inbox_name)

    def disconnect(self) -> None:
        if self._conn:
            try:
                self._conn.close()
                self._conn.logout()
            except Exception:
                pass
            self._conn = None

    def fetch_unseen(self) -> List[bytes]:
        if not self._conn:
            raise RuntimeError("IMAP not connected")
        status, messages = self._conn.search(None, "UNSEEN")
        if status != "OK":
            return []
        msg_ids = messages[0].split()
        results: List[bytes] = []
        for msg_id in msg_ids:
            status, data = self._conn.fetch(msg_id, "(RFC822)")
            if status == "OK" and data and data[0]:
                results.append(data[0][1])
        return results

    def mark_seen(self, msg_id: bytes) -> None:
        if self._conn:
            self._conn.store(msg_id, "+FLAGS", "\\Seen")


class SmtpClient:
    def __init__(self, config: EmailConfig):
        self.config = config

    def send_reply(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> None:
        if self.config.dry_run:
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.smtp_username
        msg["To"] = to_address
        msg.set_content(body)
        msg.add_attachment(
            attachment_bytes,
            maintype="application",
            subtype="octet-stream",
            filename=attachment_filename,
        )
        if self.config.smtp_use_tls:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)


def extract_sender_address(raw_email: bytes) -> str:
    msg = message_from_bytes(raw_email)
    from_header = msg.get("From", "")
    _, addr = parseaddr(from_header)
    return addr
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_client.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/megab/aegis && git add services/email_client.py tests/services/test_email_client.py
git commit -m "feat(email): add IMAP and SMTP clients"
```

---

### Task 4: Create email processor

**Files:**
- Create: `services/email_processor.py`
- Test: `tests/services/test_email_processor.py`

- [ ] **Step 1: Write the failing processor test**

Create `tests/services/test_email_processor.py`:

```python
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest
from services.email_config import EmailConfig
from services.email_job_store import EmailJobStore, JobStatus
from services.email_processor import EmailProcessor


class TestEmailProcessor:
    @pytest.fixture
    def cfg(self):
        return EmailConfig(
            enabled=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_use_ssl=True,
            imap_username="user",
            imap_password="pass",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="user",
            smtp_password="pass",
            inbox_name="INBOX",
            poll_interval_seconds=60,
            max_retries=3,
            sender_daily_limit=10,
            max_attachment_bytes=25 * 1024 * 1024,
            dry_run=False,
            system_tenant_id="system_email",
        )

    @pytest.fixture
    def store(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = EmailJobStore(path)
        yield store
        os.unlink(path)

    @pytest.fixture
    def processor(self, cfg, store):
        return EmailProcessor(cfg, store, analysis_semaphore=MagicMock())

    @pytest.mark.asyncio
    async def test_empty_email_fails_gracefully(self, processor, store):
        raw = self._build_email("a@example.com", "Empty", "", [])
        result = await processor.process_email(raw)
        assert result.should_reply is True
        assert "no usable" in result.body.lower()
        job = store.get_job_by_message_id("<empty@example.com>")
        assert job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_body_text_triggers_analysis(self, processor, store):
        raw = self._build_email(
            "a@example.com",
            "Body disclosure",
            "The defendant was charged with theft.",
            [],
        )
        with patch.object(processor, "_ingest_text"):
            with patch.object(processor, "_run_analysis", return_value={"executive_summary": "ok"}):
                with patch.object(processor, "_build_report", return_value=(b"docx", "docx")):
                    with patch.object(processor, "_send_reply") as mock_send:
                        result = await processor.process_email(raw)
                        assert result.success is True
                        mock_send.assert_called_once()

    @staticmethod
    def _build_email(sender, subject, body, attachments):
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["From"] = sender
        msg["To"] = "aegis@example.com"
        msg["Subject"] = subject
        msg["Message-ID"] = f"<{subject.lower().replace(' ', '-') or 'test'}@example.com>"
        msg.set_content(body)
        for filename, content, ctype in attachments:
            msg.add_attachment(
                content.encode(),
                maintype=ctype.split("/")[0],
                subtype=ctype.split("/")[1],
                filename=filename,
            )
        return msg.as_bytes()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_processor.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `services/email_processor.py`**

Create `services/email_processor.py`:

```python
"""Process inbound disclosure emails through the AEGIS analysis pipeline."""
import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.message import EmailMessage, Message
from email.utils import parseaddr
from pathlib import Path
from typing import List, Optional, Tuple

from services.email_client import SmtpClient, extract_sender_address
from services.email_config import EmailConfig
from services.email_job_store import EmailJobStore, JobStatus


@dataclass
class ProcessResult:
    success: bool
    should_reply: bool
    body: str
    attachment_bytes: Optional[bytes] = None
    attachment_filename: Optional[str] = None
    error_message: Optional[str] = None


class EmailProcessor:
    def __init__(
        self,
        config: EmailConfig,
        store: EmailJobStore,
        analysis_semaphore: asyncio.Semaphore,
    ):
        self.config = config
        self.store = store
        self.semaphore = analysis_semaphore
        self.smtp = SmtpClient(config)

    async def process_email(self, raw_email: bytes) -> ProcessResult:
        msg = message_from_bytes(raw_email)
        message_id = msg.get("Message-ID", "")
        sender = extract_sender_address(raw_email)
        subject = msg.get("Subject", "")

        job = self.store.create_job(
            message_id=message_id,
            sender=sender,
            subject=subject,
            attachment_count=self._count_attachments(msg),
            raw_email_bytes=raw_email,
        )

        if self._sender_over_limit(sender):
            error = f"Daily limit of {self.config.sender_daily_limit} emails exceeded."
            self.store.update_status(job.id, JobStatus.QUARANTINED, error_message=error)
            return ProcessResult(
                success=False,
                should_reply=True,
                body=self._failure_body(subject, error),
                error_message=error,
            )

        try:
            self.store.update_status(job.id, JobStatus.PARSING)
            text, attachments = self._extract_content(msg)

            if not text.strip() and not attachments:
                error = "No usable disclosure content found. Please attach a PDF, DOCX, or paste the disclosure text."
                self.store.update_status(job.id, JobStatus.FAILED, error_message=error)
                return ProcessResult(
                    success=False,
                    should_reply=True,
                    body=self._failure_body(subject, error),
                    error_message=error,
                )

            collection_name = f"temp_session_email_{job.id}"
            self._ingest_text(text, attachments, collection_name)

            self.store.update_status(job.id, JobStatus.ANALYSING)
            analysis_result = await self._run_analysis(text, collection_name)

            report_bytes, report_ext = self._build_report(analysis_result, job.id)
            filename = f"AEGIS_Disclosure_Analysis_{job.id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.{report_ext}"
            result_path = self._save_report(report_bytes, filename)

            self.store.update_status(
                job.id, JobStatus.COMPLETED, result_path=result_path
            )

            reply_body = self._success_body(subject)
            if not self.config.dry_run:
                self._send_reply(
                    sender,
                    f"AEGIS Disclosure Analysis: {subject}",
                    reply_body,
                    report_bytes,
                    filename,
                )

            return ProcessResult(
                success=True,
                should_reply=False,
                body=reply_body,
                attachment_bytes=report_bytes,
                attachment_filename=filename,
            )

        except Exception as exc:
            error = str(exc)
            self.store.increment_retry(job.id, error)
            job = self.store.get_job(job.id)
            if job.retry_count >= self.config.max_retries:
                self.store.update_status(job.id, JobStatus.QUARANTINED, error_message=error)
                return ProcessResult(
                    success=False,
                    should_reply=True,
                    body=self._failure_body(subject, error),
                    error_message=error,
                )
            return ProcessResult(
                success=False,
                should_reply=False,
                body="",
                error_message=error,
            )

    def _count_attachments(self, msg: Message) -> int:
        count = 0
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                count += 1
        return count

    def _extract_content(self, msg: Message) -> Tuple[str, List[Tuple[str, bytes]]]:
        body_text = ""
        attachments: List[Tuple[str, bytes]] = []
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == "attachment":
                filename = part.get_filename() or f"attachment_{len(attachments)}"
                payload = part.get_payload(decode=True)
                if payload:
                    attachments.append((filename, payload))
            elif content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_text += payload.decode("utf-8", errors="ignore")
            elif content_type == "text/html" and not body_text:
                payload = part.get_payload(decode=True)
                if payload:
                    html = payload.decode("utf-8", errors="ignore")
                    body_text = self._html_to_text(html)
        return body_text, attachments

    @staticmethod
    def _html_to_text(html: str) -> str:
        import re
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _sender_over_limit(self, sender: str) -> bool:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        count = self.store.get_sender_count_since(sender, since)
        return count > self.config.sender_daily_limit

    def _ingest_text(
        self,
        text: str,
        attachments: List[Tuple[str, bytes]],
        collection_name: str,
    ) -> None:
        from core.file_parser import FileParser
        from core.rag_engine import NZLegalRAG

        parser = FileParser()
        all_text = [text] if text.strip() else []
        for filename, data in attachments:
            if len(data) > self.config.max_attachment_bytes:
                continue
            try:
                doc = parser.parse_file(data, filename)
                all_text.append(f"=== {filename} ===\n{doc.content}")
            except Exception:
                continue
        combined = "\n\n".join(all_text)
        if not combined.strip():
            raise ValueError("No parseable disclosure content found.")

        db_path = os.getenv("CHROMA_DB_PATH", os.getenv("CHROMADB_PATH", "./chroma_db"))
        embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        llm_model = os.getenv("LLM_MODEL", "deepseek-r1")
        engine = NZLegalRAG(
            db_path=db_path,
            embedding_model=embedding_model,
            llm_model=llm_model,
            use_local_llm=True,
        )
        engine.ingest_text(
            text=combined,
            collection_name=collection_name,
            metadata={"source": "email_bridge"},
        )

    async def _run_analysis(self, text: str, collection_name: str) -> dict:
        from core.rag_engine import NZLegalRAG
        from core.rag_integration import create_swarm_rag

        async with self.semaphore:
            db_path = os.getenv("CHROMA_DB_PATH", os.getenv("CHROMADB_PATH", "./chroma_db"))
            embedding_model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
            llm_model = os.getenv("LLM_MODEL", "deepseek-r1")
            engine = NZLegalRAG(
                db_path=db_path,
                embedding_model=embedding_model,
                llm_model=llm_model,
                use_local_llm=True,
            )
            swarm = create_swarm_rag(engine)
            try:
                result = swarm.analyse_disclosure(
                    text, extra_collections=[collection_name]
                )
            finally:
                try:
                    from core.agent_swarm import ollama_unload_model
                    model = getattr(
                        getattr(swarm, "swarm", None), "llm_client", None
                    )
                    model_name = getattr(model, "model", os.getenv("LLM_MODEL", "deepseek-r1"))
                    if ollama_unload_model is not None:
                        await asyncio.to_thread(ollama_unload_model, model_name)
                except Exception:
                    pass
            return result

    def _build_report(self, analysis_result: dict, job_id: str) -> Tuple[bytes, str]:
        from core.report_export import build_docx, build_pdf

        try:
            docx_io = build_docx(analysis_result)
            return docx_io.getvalue(), "docx"
        except Exception as exc:
            try:
                pdf_io = build_pdf(analysis_result)
                return pdf_io.getvalue(), "pdf"
            except Exception:
                text = analysis_result.get("executive_summary", "Analysis complete.")
                return text.encode("utf-8"), "txt"

    def _save_report(self, report_bytes: bytes, filename: str) -> str:
        output_dir = Path("tenant_data/email_reports")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        path.write_bytes(report_bytes)
        return str(path)

    def _send_reply(
        self,
        to_address: str,
        subject: str,
        body: str,
        attachment_bytes: bytes,
        attachment_filename: str,
    ) -> None:
        self.smtp.send_reply(to_address, subject, body, attachment_bytes, attachment_filename)

    def _success_body(self, original_subject: str) -> str:
        return (
            "Thank you for using AEGIS.\n\n"
            f"Your disclosure \"{original_subject}\" has been analysed and the brief is attached.\n\n"
            "DISCLAIMER: This analysis is generated by AI and does not constitute legal advice. "
            "Consult a qualified barrister."
        )

    def _failure_body(self, original_subject: str, reason: str) -> str:
        return (
            "Thank you for using AEGIS.\n\n"
            f"We could not analyse your disclosure \"{original_subject}\": {reason}\n\n"
            "Please ensure you attach a supported file (PDF, DOCX, DOC, TXT, XLSX, HTML, MD, CSV, JSON) "
            "or paste the disclosure text in the email body.\n\n"
            "DISCLAIMER: This message is generated by AI and does not constitute legal advice."
        )

    async def process_batch(self, raw_emails: List[bytes]) -> List[ProcessResult]:
        results = []
        for raw in raw_emails:
            try:
                results.append(await self.process_email(raw))
            except Exception as exc:
                results.append(
                    ProcessResult(
                        success=False,
                        should_reply=False,
                        body="",
                        error_message=str(exc),
                    )
                )
        return results
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_processor.py -v
```

Expected: PASS (the mocked analysis path should succeed; empty-body path should fail gracefully).

- [ ] **Step 5: Commit**

```bash
cd C:/Users/megab/aegis && git add services/email_processor.py tests/services/test_email_processor.py
git commit -m "feat(email): add email processor with analysis pipeline integration"
```

---

### Task 5: Create poller and wire into API lifespan

**Files:**
- Create: `services/email_poller.py`
- Modify: `api/server.py:431-445` (lifespan) and add include near other routers
- Test: `tests/services/test_email_poller.py`

- [ ] **Step 1: Write the failing poller test**

Create `tests/services/test_email_poller.py`:

```python
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from services.email_config import EmailConfig
from services.email_poller import EmailPoller


class TestEmailPoller:
    @pytest.fixture
    def cfg(self):
        return EmailConfig(
            enabled=True,
            imap_host="imap.example.com",
            imap_port=993,
            imap_use_ssl=True,
            imap_username="user",
            imap_password="pass",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_use_tls=True,
            smtp_username="user",
            smtp_password="pass",
            inbox_name="INBOX",
            poll_interval_seconds=60,
            max_retries=3,
            sender_daily_limit=10,
            max_attachment_bytes=25 * 1024 * 1024,
            dry_run=False,
            system_tenant_id="system_email",
        )

    @pytest.mark.asyncio
    async def test_poll_once(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(return_value=[MagicMock(success=True)])
        poller = EmailPoller(cfg, processor, MagicMock())
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [b"email-1"]
            MockImap.return_value = mock_conn
            await poller.poll_once()
            mock_conn.connect.assert_called_once()
            mock_conn.fetch_unseen.assert_called_once()
            processor.process_batch.assert_awaited_once_with([b"email-1"])
            mock_conn.disconnect.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_poller.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `services/email_poller.py`**

Create `services/email_poller.py`:

```python
"""Background poller for inbound disclosure emails."""
import asyncio
import logging
from typing import Optional

from services.email_client import ImapClient
from services.email_config import EmailConfig
from services.email_processor import EmailProcessor

logger = logging.getLogger(__name__)


class EmailPoller:
    def __init__(
        self,
        config: EmailConfig,
        processor: EmailProcessor,
        imap_client: Optional[ImapClient] = None,
    ):
        self.config = config
        self.processor = processor
        self.imap_client = imap_client
        self._stop_event = asyncio.Event()

    async def poll_once(self) -> None:
        client = self.imap_client or ImapClient(self.config)
        try:
            client.connect()
            raw_emails = client.fetch_unseen()
            if raw_emails:
                logger.info("Fetched %d unseen email(s)", len(raw_emails))
                await self.processor.process_batch(raw_emails)
        except Exception as exc:
            logger.error("Email poll failed: %s", exc)
        finally:
            client.disconnect()

    async def run(self) -> None:
        while not self._stop_event.is_set():
            if self.config.enabled:
                await self.poll_once()
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=self.config.poll_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass

    def stop(self) -> None:
        self._stop_event.set()


async def _email_poller_task(
    config: EmailConfig,
    processor: EmailProcessor,
) -> None:
    poller = EmailPoller(config, processor)
    await poller.run()


def start_email_poller(
    config: EmailConfig,
    processor: EmailProcessor,
) -> asyncio.Task:
    return asyncio.create_task(_email_poller_task(config, processor))
```

- [ ] **Step 4: Modify `api/server.py` lifespan to start the poller**

Edit `api/server.py`:

Find lines 431-445:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    global tenant_manager
    if TenantManager is not None:
        tenant_manager = TenantManager(storage_dir=os.getenv("TENANT_DATA_PATH", "./tenant_data"))
    purge_expired_demo_state()
    cleanup_task = asyncio.create_task(_cleanup_temp_collections_task())
    try:
        yield
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
```

Replace with:

```python
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_poller.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/megab/aegis && git add services/email_poller.py tests/services/test_email_poller.py api/server.py
git commit -m "feat(email): add background email poller and wire into API lifespan"
```

---

### Task 6: Add FastAPI admin endpoints

**Files:**
- Create: `api/email_routes.py`
- Modify: `api/server.py` to include router
- Test: `tests/api/test_email_routes.py`

- [ ] **Step 1: Write the failing routes test**

Create `tests/api/test_email_routes.py`:

```python
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from api.server import app


class TestEmailRoutes:
    def test_email_health_disabled(self):
        with patch("api.email_routes.get_email_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(enabled=False)
            client = TestClient(app)
            response = client.get("/api/v1/email/health")
            assert response.status_code == 200
            assert response.json()["enabled"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/api/test_email_routes.py -v
```

Expected: FAIL with `ModuleNotFoundError` or 404.

- [ ] **Step 3: Implement `api/email_routes.py`**

Create `api/email_routes.py`:

```python
"""Admin endpoints for the email disclosure bridge."""
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import get_current_demo_or_tenant
from services.email_client import ImapClient, SmtpClient
from services.email_config import EmailConfig, get_email_config
from services.email_job_store import EmailJobStore, JobStatus
from services.email_poller import EmailPoller
from services.email_processor import EmailProcessor

router = APIRouter(prefix="/api/v1/email", tags=["email"])


def _get_store() -> EmailJobStore:
    import os
    db_path = os.path.join(
        os.getenv("TENANT_DATA_PATH", "./tenant_data"), "email_jobs.db"
    )
    return EmailJobStore(db_path)


@router.get("/health")
async def email_health() -> dict:
    cfg = get_email_config()
    result = {
        "enabled": cfg.enabled,
        "imap_host": cfg.imap_host,
        "smtp_host": cfg.smtp_host,
        "poll_interval_seconds": cfg.poll_interval_seconds,
    }
    if not cfg.enabled:
        return result
    imap_ok = False
    smtp_ok = False
    try:
        client = ImapClient(cfg)
        client.connect()
        client.disconnect()
        imap_ok = True
    except Exception as exc:
        result["imap_error"] = str(exc)
    try:
        client = SmtpClient(cfg)
        # We only test connect + ehlo; avoid sending real email.
        import smtplib
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=10) as server:
            server.starttls()
            server.login(cfg.smtp_username, cfg.smtp_password)
        smtp_ok = True
    except Exception as exc:
        result["smtp_error"] = str(exc)
    result["imap_ok"] = imap_ok
    result["smtp_ok"] = smtp_ok
    return result


@router.post("/fetch")
async def email_fetch(
    tenant: Any = Depends(get_current_demo_or_tenant),
) -> dict:
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
    tenant: Any = Depends(get_current_demo_or_tenant),
) -> dict:
    store = _get_store()
    since = datetime.now(timezone.utc) - timedelta(days=days)
    job_status = JobStatus(status) if status else None
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
    tenant: Any = Depends(get_current_demo_or_tenant),
) -> dict:
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
    tenant: Any = Depends(get_current_demo_or_tenant),
) -> dict:
    cfg = get_email_config()
    if not cfg.enabled:
        raise HTTPException(status_code=400, detail="Email bridge not enabled")
    store = _get_store()
    job = store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.raw_email_bytes:
        raise HTTPException(status_code=400, detail="Original email not available for retry")
    from api.server import _analysis_semaphore
    processor = EmailProcessor(cfg, store, _analysis_semaphore)
    result = await processor.process_email(job.raw_email_bytes)
    return {"success": result.success, "error": result.error_message}


@router.get("/metrics")
async def email_metrics(
    tenant: Any = Depends(get_current_demo_or_tenant),
) -> dict:
    store = _get_store()
    return {"counts": store.get_counts()}
```

- [ ] **Step 4: Include router in `api/server.py`**

Find where other routers are included (near `app.include_router(auth_router, ...)`). Add:

```python
try:
    from api.email_routes import router as email_router
    app.include_router(email_router)
except ImportError:
    pass
```

- [ ] **Step 5: Run tests to verify they pass**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/api/test_email_routes.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd C:/Users/megab/aegis && git add api/email_routes.py tests/api/test_email_routes.py api/server.py
git commit -m "feat(email): add admin endpoints for email bridge"
```

---

### Task 7: Add Streamlit "Email Inbox" page

**Files:**
- Modify: `web/streamlit_app.py` (add sidebar entry and page function)

- [ ] **Step 1: Add sidebar entry and page function**

In `web/streamlit_app.py`, update `show_sidebar()` to include "Email Inbox" for admin/staff roles, and add a branch in `main()`.

In `show_sidebar()`, add "Email Inbox" to the admin and staff page lists:

```python
        if role == "admin":
            pages = [
                "Search",
                "Upload",
                "Defence Analysis",
                "Collection Manager",
                "Collection Inspector",
                "Admin Panel",
                "Email Inbox",
            ]
        elif role in ["staff", "adminstaff"]:
            pages = [
                "Search",
                "Upload",
                "Defence Analysis",
                "Collection Manager",
                "Collection Inspector",
                "Email Inbox",
            ]
```

Add a new function before `main()`:

```python
def show_email_inbox():
    import os
    st.title("📧 Email Inbox")
    st.caption("Disclosure submissions received by email.")

    status_filter = st.selectbox(
        "Status",
        ["all", "received", "parsing", "analysing", "completed", "failed", "quarantined"],
    )
    days = st.slider("Days", 1, 30, 7)
    apikey = st.session_state.get("apikey")

    if st.button("🔄 Fetch now"):
        result = api_call("/api/v1/email/fetch", method="POST", apikey=apikey, readtimeout=120)
        if isinstance(result, dict) and result.get("status") == "ok":
            st.success("Fetch triggered")
        else:
            st.error(f"Fetch failed: {result}")

    params = {"days": days, "limit": 200}
    if status_filter != "all":
        params["status"] = status_filter
    result = api_call("/api/v1/email/jobs", method="GET", data=params, apikey=apikey, readtimeout=30)
    if not isinstance(result, dict):
        st.error(f"Failed to load jobs: {result}")
        return
    jobs = result.get("jobs", [])

    st.write(f"Found {len(jobs)} job(s)")
    for job in jobs:
        with st.expander(f"{job['subject']} — {job['status']} ({job['sender']})"):
            st.write(f"Received: {job['received_at']}")
            st.write(f"Attachments: {job['attachment_count']}")
            st.write(f"Retries: {job['retry_count']}")
            if job.get("error_message"):
                st.error(job["error_message"])
            if job.get("result_path") and os.path.exists(job["result_path"]):
                with open(job["result_path"], "rb") as f:
                    st.download_button(
                        label="Download report",
                        data=f.read(),
                        file_name=os.path.basename(job["result_path"]),
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    )
            if job["status"] in ("failed", "quarantined"):
                if st.button("Retry", key=f"retry_{job['id']}"):
                    rr = api_call(
                        f"/api/v1/email/jobs/{job['id']}/retry",
                        method="POST",
                        apikey=apikey,
                        readtimeout=120,
                    )
                    st.info(rr if isinstance(rr, str) else rr.get("detail", str(rr)))
```

In `main()`, add:

```python
elif page == "Email Inbox":
    show_email_inbox()
```

- [ ] **Step 2: Verify the web app imports**

Run:
```bash
cd C:/Users/megab/aegis && python -c "import web.streamlit_app"
```

Expected: no ImportError.

- [ ] **Step 3: Commit**

```bash
cd C:/Users/megab/aegis && git add web/streamlit_app.py
git commit -m "feat(email): add Streamlit email inbox page"
```

---

### Task 8: Add environment example, test deps, and update docs

**Files:**
- Create or modify: `.env.example`
- Modify: `requirements.txt`
- Modify: `docs/superpowers/specs/2026-06-28-aegis-email-disclosure-design.md` if plan deviates (it shouldn't).

- [ ] **Step 1: Add test dependencies to `requirements.txt`**

Append:

```text
# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Add email env vars to `.env.example`**

Create or append to `.env.example`:

```bash
# AEGIS Email Disclosure Bridge
# Set AEGIS_EMAIL_POLLER_ENABLED=true to enable inbound email analysis.
AEGIS_EMAIL_POLLER_ENABLED=false
AEGIS_EMAIL_DRY_RUN=false
AEGIS_EMAIL_IMAP_HOST=imap.example.com
AEGIS_EMAIL_IMAP_PORT=993
AEGIS_EMAIL_IMAP_USE_SSL=true
AEGIS_EMAIL_IMAP_USERNAME=aegis@example.com
AEGIS_EMAIL_IMAP_PASSWORD=changeme
AEGIS_EMAIL_SMTP_HOST=smtp.example.com
AEGIS_EMAIL_SMTP_PORT=587
AEGIS_EMAIL_SMTP_USE_TLS=true
AEGIS_EMAIL_SMTP_USERNAME=aegis@example.com
AEGIS_EMAIL_SMTP_PASSWORD=changeme
AEGIS_EMAIL_INBOX_NAME=INBOX
AEGIS_EMAIL_POLL_INTERVAL_SECONDS=60
AEGIS_EMAIL_MAX_RETRIES=3
AEGIS_EMAIL_SENDER_DAILY_LIMIT=10
AEGIS_EMAIL_MAX_ATTACHMENT_BYTES=26214400
AEGIS_EMAIL_SYSTEM_TENANT_ID=system_email
```

- [ ] **Step 2: Commit**

```bash
cd C:/Users/megab/aegis && git add .env.example requirements.txt
git commit -m "docs(email): add email bridge environment variables and test deps"
```

---

### Task 9: Integration and regression testing

**Files:**
- Existing: `tests/`

- [ ] **Step 1: Run the new test suite**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/services/test_email_config.py tests/services/test_email_job_store.py tests/services/test_email_client.py tests/services/test_email_processor.py tests/services/test_email_poller.py tests/api/test_email_routes.py -v
```

Expected: all PASS.

- [ ] **Step 2: Run existing disclosure analysis regression tests**

Run:
```bash
cd C:/Users/megab/aegis && pytest tests/test_pipeline.py -v
```

Expected: PASS (or same baseline as before changes).

- [ ] **Step 3: Lint / type check**

Run:
```bash
cd C:/Users/megab/aegis && python -m py_compile services/*.py api/email_routes.py
```

Expected: no syntax errors.

- [ ] **Step 4: Commit**

```bash
cd C:/Users/megab/aegis && git commit -m "test(email): verify email bridge and regression tests pass" --allow-empty
```

---

## Self-Review Checklist

- [ ] **Spec coverage:** Every requirement in `2026-06-28-aegis-email-disclosure-design.md` maps to a task above.
- [ ] **Placeholder scan:** No TBD, TODO, or vague steps remain.
- [ ] **Type consistency:** `EmailConfig` fields, `JobStatus` enum, and endpoint names match between files.
- [ ] **No git mutations without permission:** Commits in this plan are explicit but optional during execution; do not run `git push`.
