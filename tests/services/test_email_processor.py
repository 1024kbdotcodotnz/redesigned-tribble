import asyncio
import os
import tempfile
from dataclasses import replace
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
        with patch.object(processor, "_send_reply") as mock_send:
            result = await processor.process_email(raw)
        assert result.should_reply is True
        assert "no usable" in result.body.lower()
        job = store.get_job_by_message_id("<empty@example.com>")
        assert job.status == JobStatus.FAILED
        mock_send.assert_called_once()
        assert "no usable" in mock_send.call_args[0][2].lower()

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

    @pytest.mark.asyncio
    async def test_unparseable_attachment_fails_gracefully(self, processor, store):
        raw = self._build_email(
            "a@example.com",
            "Bad attachment",
            "",
            [("bad.zip", "not a real zip", "application/zip")],
        )
        with patch.object(processor, "_send_reply") as mock_send:
            result = await processor.process_email(raw)
        assert result.should_reply is True
        job = store.get_job_by_message_id("<bad-attachment@example.com>")
        assert job.status == JobStatus.FAILED
        mock_send.assert_called_once()
        assert "no usable" in mock_send.call_args[0][2].lower()

    @pytest.mark.asyncio
    async def test_supported_but_unparseable_attachment_fails_gracefully(self, processor, store):
        from core.file_parser import FileParser

        raw = self._build_email(
            "a@example.com",
            "Bad txt attachment",
            "",
            [("bad.txt", "not parseable", "text/plain")],
        )

        def mock_ingest(text, attachments, collection_name):
            parser = FileParser()
            all_text = [text] if text.strip() else []
            for filename, data in attachments:
                try:
                    doc = parser.parse_file(data, filename)
                    all_text.append(f"=== {filename} ===\n{doc.content}")
                except Exception:
                    continue
            combined = "\n\n".join(all_text)
            if not combined.strip():
                raise ValueError("No parseable disclosure content found.")

        with patch.object(FileParser, "parse_file", side_effect=ValueError("bad")):
            with patch.object(processor, "_ingest_text", side_effect=mock_ingest):
                with patch.object(processor, "_send_reply") as mock_send:
                    result = await processor.process_email(raw)
        assert result.should_reply is True
        assert result.success is False
        job = store.get_job_by_message_id("<bad-txt-attachment@example.com>")
        assert job.status == JobStatus.FAILED
        mock_send.assert_called_once()
        assert "no usable" in mock_send.call_args[0][2].lower()

    @pytest.mark.asyncio
    async def test_retry_job_resets_and_reprocesses(self, processor, store):
        raw = self._build_email(
            "retry@example.com",
            "Retry disclosure",
            "The defendant was charged with theft.",
            [],
        )
        job = store.create_job(
            message_id="<retry-disclosure@example.com>",
            sender="retry@example.com",
            subject="Retry disclosure",
            attachment_count=0,
            raw_email_bytes=raw,
        )
        store.update_status(job.id, JobStatus.FAILED, error_message="previous failure")
        store.increment_retry(job.id, "previous failure")

        with patch.object(processor, "_ingest_text"):
            with patch.object(
                processor, "_run_analysis", return_value={"executive_summary": "ok"}
            ):
                with patch.object(
                    processor, "_build_report", return_value=(b"docx", "docx")
                ):
                    with patch.object(processor, "_send_reply"):
                        result = await processor.retry_job(job.id)
                        assert result.success is True

        retried = store.get_job(job.id)
        assert retried.status == JobStatus.COMPLETED
        assert retried.retry_count == 0

    @pytest.mark.asyncio
    async def test_end_to_end_with_real_parser_and_report(self, cfg, store, tmp_path):
        processor = EmailProcessor(cfg, store, asyncio.Semaphore(1))
        text = "The defendant is charged with theft. The complainant alleges the defendant took a laptop."
        raw = self._build_email(
            "a@example.com",
            "Disclosure",
            "",
            [("disclosure.txt", text, "text/plain")],
        )
        analysis = {
            "executive_summary": "Test summary",
            "charge_and_legislative_framework": "Theft",
            "summary_of_evidence": "Complainant testimony",
            "assessment_of_prosecution_case": "Moderate",
            "evidence_analysis": "CCTV and witness",
            "elements_of_the_offence": "Dishonest appropriation",
            "defence_strategies": "Denial",
            "cross_examination_priorities": "Complainant reliability",
            "disclosure_and_forensic_gaps": "Chain of custody",
            "instructions_to_counsel_pre_trial": "Interview witnesses",
            "evidentiary_issues_to_raise": "Hearsay",
            "conclusion": "Defence viable",
        }

        import sys
        import types

        class FakeRAG:
            def __init__(self, **kwargs):
                pass

            def ingest_text(self, **kwargs):
                pass

        fake_module = types.SimpleNamespace(NZLegalRAG=FakeRAG)
        with patch.dict(sys.modules, {"core.rag_engine": fake_module}):
            with patch.object(processor, "_run_analysis", return_value=analysis):
                with patch.object(processor.smtp, "send_reply") as mock_send:
                    result = await processor.process_email(raw)
                    assert result.success is True
                    assert result.attachment_filename.endswith(".docx")
                    job = store.get_job_by_message_id("<disclosure@example.com>")
                    assert job.status == JobStatus.COMPLETED
                    assert job.result_path is not None
                    assert os.path.exists(job.result_path)
                    mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_dry_run_does_not_send_reply(self, cfg, store):
        cfg = replace(cfg, dry_run=True)
        processor = EmailProcessor(cfg, store, asyncio.Semaphore(1))
        raw = self._build_email("a@example.com", "Dry", "Some disclosure text", [])
        with patch.object(processor, "_ingest_text"):
            with patch.object(
                processor, "_run_analysis", return_value={"executive_summary": "ok"}
            ):
                with patch.object(
                    processor, "_build_report", return_value=(b"docx", "docx")
                ):
                    with patch.object(processor.smtp, "send_reply") as mock_send:
                        result = await processor.process_email(raw)
                        assert result.success is True
                        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_sender_rate_limit(self, cfg, store):
        cfg = replace(cfg, sender_daily_limit=1)
        processor = EmailProcessor(cfg, store, asyncio.Semaphore(1))
        raw1 = self._build_email("a@example.com", "First", "text", [])
        raw2 = self._build_email("a@example.com", "Second", "text", [])
        with patch.object(processor, "_ingest_text"):
            with patch.object(
                processor, "_run_analysis", return_value={"executive_summary": "ok"}
            ):
                with patch.object(
                    processor, "_build_report", return_value=(b"docx", "docx")
                ):
                    with patch.object(processor.smtp, "send_reply"):
                        result1 = await processor.process_email(raw1)
                        result2 = await processor.process_email(raw2)
                        assert result1.success is True
                        assert result2.success is False
                        assert result2.should_reply is True
                        assert "limit" in result2.body.lower()

    @pytest.mark.asyncio
    async def test_rate_limit_sends_failure_reply(self, cfg, store):
        cfg = replace(cfg, sender_daily_limit=1)
        processor = EmailProcessor(cfg, store, asyncio.Semaphore(1))
        raw1 = self._build_email("a@example.com", "First", "text", [])
        raw2 = self._build_email("a@example.com", "Second", "text", [])
        with patch.object(processor, "_ingest_text"):
            with patch.object(
                processor, "_run_analysis", return_value={"executive_summary": "ok"}
            ):
                with patch.object(
                    processor, "_build_report", return_value=(b"docx", "docx")
                ):
                    with patch.object(processor, "_send_reply") as mock_send:
                        await processor.process_email(raw1)
                        await processor.process_email(raw2)
                        assert mock_send.call_count == 2
                        failure_call = next(
                            call for call in mock_send.call_args_list
                            if "limit" in call.args[2].lower()
                        )
                        call_args = failure_call.args
                        assert call_args[0] == "a@example.com"
                        assert "Second" in call_args[1]
                        assert call_args[3] == b""
                        assert call_args[4] == ""

    @pytest.mark.asyncio
    async def test_max_retries_sends_failure_reply(self, processor, store):
        raw = self._build_email("a@example.com", "Retries", "text", [])
        with patch.object(processor, "_ingest_text", side_effect=RuntimeError("boom")):
            with patch.object(processor, "_send_reply") as mock_send:
                for attempt in range(processor.config.max_retries):
                    result = await processor.process_email(raw)
                    assert result.success is False
                    if attempt < processor.config.max_retries - 1:
                        assert result.should_reply is False
                        mock_send.assert_not_called()
                    else:
                        assert result.should_reply is True
                        mock_send.assert_called_once()
                        call_args = mock_send.call_args[0]
                        assert call_args[0] == "a@example.com"
                        assert "Retries" in call_args[1]
                        assert "try again later" in call_args[2].lower()
                        assert call_args[3] == b""
                        assert call_args[4] == ""

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
