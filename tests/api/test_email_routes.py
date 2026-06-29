import os
import tempfile
from email.message import EmailMessage
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from api.server import app, get_current_demo_or_tenant
from services.email_job_store import EmailJobStore, JobStatus


class TestEmailRoutes:
    @pytest.fixture
    def client(self):
        from api.email_routes import _get_current_demo_or_tenant

        app.dependency_overrides[_get_current_demo_or_tenant] = lambda: {
            "role": "admin"
        }
        try:
            yield TestClient(app)
        finally:
            app.dependency_overrides.pop(_get_current_demo_or_tenant, None)

    @pytest.fixture
    def real_store(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            path = f.name
        store = EmailJobStore(path)
        yield store
        os.unlink(path)

    @staticmethod
    def _build_email(sender, subject, body, attachments=None):
        if attachments is None:
            attachments = []
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

    def test_email_health_disabled(self, client):
        with patch("api.email_routes.get_email_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(enabled=False)
            response = client.get("/api/v1/email/health")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False

    def test_health_disabled_redacts_config(self, client):
        with patch("api.email_routes.get_email_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                enabled=False,
                imap_host="imap.example.com",
                smtp_host="smtp.example.com",
                poll_interval_seconds=60,
            )
            response = client.get("/api/v1/email/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"enabled": False}

    def test_email_health_enabled(self, client):
        cfg = MagicMock(
            enabled=True,
            imap_host="imap.example.com",
            smtp_host="smtp.example.com",
            poll_interval_seconds=60,
        )
        with patch("api.email_routes.get_email_config", return_value=cfg):
            with patch(
                "api.email_routes._check_imap", return_value=(True, None)
            ) as mock_imap:
                with patch(
                    "api.email_routes._check_smtp", return_value=(True, None)
                ) as mock_smtp:
                    response = client.get("/api/v1/email/health")
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True
        assert data["imap_ok"] is True
        assert data["smtp_ok"] is True
        mock_imap.assert_awaited_once_with(cfg)
        mock_smtp.assert_awaited_once_with(cfg)

    def test_email_health_with_errors(self, client):
        cfg = MagicMock(
            enabled=True,
            imap_host="imap.example.com",
            smtp_host="smtp.example.com",
            poll_interval_seconds=60,
        )
        with patch("api.email_routes.get_email_config", return_value=cfg):
            with patch(
                "api.email_routes._check_imap", return_value=(False, "imap down")
            ):
                with patch(
                    "api.email_routes._check_smtp", return_value=(False, "smtp down")
                ):
                    response = client.get("/api/v1/email/health")
        assert response.status_code == 200
        data = response.json()
        assert data["imap_ok"] is False
        assert data["smtp_ok"] is False
        assert data["imap_error"] == "imap down"
        assert data["smtp_error"] == "smtp down"

    def test_email_fetch_disabled(self, client):
        with patch("api.email_routes.get_email_config") as mock_cfg:
            mock_cfg.return_value = MagicMock(enabled=False)
            response = client.post("/api/v1/email/fetch")
        assert response.status_code == 400
        assert response.json()["detail"] == "Email bridge not enabled"

    def test_email_fetch_enabled(self, client):
        cfg = MagicMock(enabled=True)
        with patch("api.email_routes.get_email_config", return_value=cfg):
            with patch(
                "api.email_routes.EmailPoller.poll_once", new_callable=AsyncMock
            ) as mock_poll:
                response = client.post("/api/v1/email/fetch")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_poll.assert_awaited_once()

    def test_list_jobs(self, client):
        now = MagicMock()
        now.isoformat.return_value = "2024-01-01T00:00:00+00:00"
        job = MagicMock(
            id="job-1",
            message_id="msg-1",
            sender="sender@example.com",
            subject="Test",
            received_at=now,
            attachment_count=0,
            status=JobStatus.COMPLETED,
            retry_count=0,
            result_path=None,
            error_message=None,
            updated_at=now,
        )
        store = MagicMock()
        store.list_jobs.return_value = [job]
        with patch("api.email_routes._get_store", return_value=store):
            response = client.get("/api/v1/email/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["id"] == "job-1"

    def test_list_jobs_invalid_status_returns_422(self, client):
        response = client.get("/api/v1/email/jobs?status=not_a_status")
        assert response.status_code == 422
        assert "Invalid status" in response.json()["detail"]

    def test_list_jobs_with_real_store(self, client, real_store, monkeypatch):
        monkeypatch.setattr("api.email_routes._store_cache", real_store)
        raw = self._build_email("a@example.com", "Test subject", "body text", [])
        real_store.create_job("<m1>", "a@example.com", "Subj", 0, raw)
        response = client.get("/api/v1/email/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
        assert data["jobs"][0]["sender"] == "a@example.com"

    def test_get_job_missing(self, client):
        store = MagicMock()
        store.get_job.return_value = None
        with patch("api.email_routes._get_store", return_value=store):
            response = client.get("/api/v1/email/jobs/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    def test_get_job_existing(self, client):
        now = MagicMock()
        now.isoformat.return_value = "2024-01-01T00:00:00+00:00"
        job = MagicMock(
            id="job-1",
            message_id="msg-1",
            sender="sender@example.com",
            subject="Test",
            received_at=now,
            attachment_count=0,
            status=JobStatus.COMPLETED,
            retry_count=0,
            result_path=None,
            error_message=None,
            updated_at=now,
        )
        store = MagicMock()
        store.get_job.return_value = job
        with patch("api.email_routes._get_store", return_value=store):
            response = client.get("/api/v1/email/jobs/job-1")
        assert response.status_code == 200
        assert response.json()["id"] == "job-1"

    def test_retry_job_non_retryable_status(self, client, real_store):
        cfg = MagicMock(enabled=True)
        raw = self._build_email("sender@example.com", "Completed", "body text", [])
        job = real_store.create_job(
            message_id="<completed@example.com>",
            sender="sender@example.com",
            subject="Completed",
            attachment_count=0,
            raw_email_bytes=raw,
        )
        real_store.update_status(job.id, JobStatus.COMPLETED)
        with patch("api.email_routes.get_email_config", return_value=cfg):
            with patch("api.email_routes._get_store", return_value=real_store):
                response = client.post(f"/api/v1/email/jobs/{job.id}/retry")
        assert response.status_code == 400
        assert "cannot be retried" in response.json()["detail"]

    def test_retry_job_failed(self, client, real_store):
        cfg = MagicMock(enabled=True, sender_daily_limit=10, max_retries=3, dry_run=True)
        raw = self._build_email(
            "sender@example.com", "Failed disclosure", "The defendant was charged.", []
        )
        job = real_store.create_job(
            message_id="<failed-disclosure@example.com>",
            sender="sender@example.com",
            subject="Failed disclosure",
            attachment_count=0,
            raw_email_bytes=raw,
        )
        real_store.update_status(job.id, JobStatus.FAILED, error_message="boom")
        real_store.increment_retry(job.id, "boom")

        with patch("api.email_routes.get_email_config", return_value=cfg):
            with patch("api.email_routes._get_store", return_value=real_store):
                with patch("api.email_routes.EmailProcessor._ingest_text"):
                    with patch(
                        "api.email_routes.EmailProcessor._run_analysis",
                        new=AsyncMock(return_value={"executive_summary": "ok"}),
                    ):
                        with patch(
                            "api.email_routes.EmailProcessor._build_report",
                            return_value=(b"docx", "docx"),
                        ):
                            response = client.post(f"/api/v1/email/jobs/{job.id}/retry")
        assert response.status_code == 200
        assert response.json() == {"success": True, "error": None}

        retried = real_store.get_job(job.id)
        assert retried.status == JobStatus.COMPLETED
        assert retried.retry_count == 0

    def test_retry_job_quarantined(self, client, real_store):
        cfg = MagicMock(enabled=True, sender_daily_limit=10, max_retries=1, dry_run=True)
        raw = self._build_email(
            "sender@example.com", "Quarantined disclosure", "The defendant was charged.", []
        )
        job = real_store.create_job(
            message_id="<quarantined-disclosure@example.com>",
            sender="sender@example.com",
            subject="Quarantined disclosure",
            attachment_count=0,
            raw_email_bytes=raw,
        )
        real_store.update_status(job.id, JobStatus.QUARANTINED, error_message="boom")
        real_store.increment_retry(job.id, "boom")
        real_store.increment_retry(job.id, "boom")

        with patch("api.email_routes.get_email_config", return_value=cfg):
            with patch("api.email_routes._get_store", return_value=real_store):
                with patch("api.email_routes.EmailProcessor._ingest_text"):
                    with patch(
                        "api.email_routes.EmailProcessor._run_analysis",
                        new=AsyncMock(side_effect=Exception("boom")),
                    ):
                        response = client.post(f"/api/v1/email/jobs/{job.id}/retry")
        assert response.status_code == 200
        assert response.json() == {"success": False, "error": "boom"}

        retried = real_store.get_job(job.id)
        assert retried.status == JobStatus.QUARANTINED
        assert retried.retry_count == 1

    def test_email_metrics(self, client):
        store = MagicMock()
        store.get_counts.return_value = {
            "received": 1,
            "parsing": 0,
            "analysing": 0,
            "completed": 2,
            "failed": 0,
            "quarantined": 0,
            "total": 3,
        }
        with patch("api.email_routes._get_store", return_value=store):
            response = client.get("/api/v1/email/metrics")
        assert response.status_code == 200
        assert response.json()["counts"]["total"] == 3

    def test_email_metrics_with_real_store(self, client, real_store, monkeypatch):
        monkeypatch.setattr("api.email_routes._store_cache", real_store)
        raw = self._build_email("a@example.com", "Metrics test", "body text", [])
        real_store.create_job("<m2>", "a@example.com", "Metrics test", 0, raw)
        response = client.get("/api/v1/email/metrics")
        assert response.status_code == 200
        data = response.json()
        assert data["counts"]["received"] == 1
        assert data["counts"]["total"] == 1

    def test_get_job_report_missing_job(self, client):
        response = client.get("/api/v1/email/jobs/nonexistent/report")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"

    def test_get_job_report_missing_file(self, client, real_store, monkeypatch):
        monkeypatch.setattr("api.email_routes._store_cache", real_store)
        raw = self._build_email("a@example.com", "Report test", "body text", [])
        job = real_store.create_job("<report-missing>", "a@example.com", "Report test", 0, raw)
        real_store.update_status(job.id, JobStatus.COMPLETED, result_path="/tmp/does_not_exist.docx")
        response = client.get(f"/api/v1/email/jobs/{job.id}/report")
        assert response.status_code == 404
        assert response.json()["detail"] == "Report not found"

    def test_get_job_report_success(self, client, real_store, monkeypatch, tmp_path):
        monkeypatch.setattr("api.email_routes._store_cache", real_store)
        raw = self._build_email("a@example.com", "Report test", "body text", [])
        job = real_store.create_job("<report-success>", "a@example.com", "Report test", 0, raw)
        report_path = tmp_path / "report.docx"
        report_content = b"fake docx content"
        report_path.write_bytes(report_content)
        real_store.update_status(job.id, JobStatus.COMPLETED, result_path=str(report_path))
        response = client.get(f"/api/v1/email/jobs/{job.id}/report")
        assert response.status_code == 200
        assert response.content == report_content
        assert response.headers["content-type"] == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_analyse_disclosure_endpoint_still_works(self, client):
        app.dependency_overrides[get_current_demo_or_tenant] = lambda: {"role": "admin"}
        try:
            with patch("api.server.get_rag_engine", return_value=None):
                response = client.post(
                    "/api/v1/analyse/disclosure",
                    json={
                        "disclosure_text": "The defendant is charged with theft.",
                        "analysis_type": "full",
                    },
                )
            assert response.status_code in (200, 503)
        finally:
            app.dependency_overrides.pop(get_current_demo_or_tenant, None)
