"""SQLite job store for email disclosure analysis jobs."""
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Iterator, List, Optional


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

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
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
        now = self._now()
        job_id = str(uuid.uuid4())
        try:
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
        except sqlite3.IntegrityError:
            existing = self.get_job_by_message_id(message_id)
            if existing:
                return existing
            raise
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
        fields = ["status = ?"]
        params = [status.value]
        if result_path is not None:
            fields.append("result_path = ?")
            params.append(result_path)
        if error_message is not None:
            fields.append("error_message = ?")
            params.append(error_message)
        fields.append("updated_at = ?")
        params.append(self._now())
        params.append(job_id)
        with self._connect() as conn:
            cursor = conn.execute(
                f"UPDATE email_jobs SET {', '.join(fields)} WHERE id = ?",
                params,
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Job {job_id} not found")

    def increment_retry(self, job_id: str, error_message: str) -> None:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE email_jobs
                SET retry_count = retry_count + 1, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (error_message, self._now(), job_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Job {job_id} not found")

    def reset_for_retry(self, job_id: str) -> None:
        """Reset a job to RECEIVED and clear its retry state."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE email_jobs
                SET status = ?, retry_count = 0, error_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (JobStatus.RECEIVED.value, self._now(), job_id),
            )
            if cursor.rowcount == 0:
                raise ValueError(f"Job {job_id} not found")

    def list_jobs(
        self,
        status: Optional[JobStatus] = None,
        since: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EmailJob]:
        if limit < 0 or offset < 0:
            raise ValueError("limit and offset must be non-negative")
        query = "SELECT * FROM email_jobs WHERE 1=1"
        params: List = []
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if since:
            query += " AND received_at >= ?"
            params.append(since.isoformat())
        query += " ORDER BY received_at DESC, id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_job(row) for row in rows]

    def get_counts(self) -> Dict[str, int]:
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
