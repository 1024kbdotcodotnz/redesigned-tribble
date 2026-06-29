import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from services.email_config import EmailConfig
from services.email_job_store import JobStatus
from services.email_poller import EmailPoller
from services.email_processor import ProcessResult


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
        processor.process_batch = AsyncMock(
            return_value=[ProcessResult(success=True, should_reply=False, body="")]
        )
        poller = EmailPoller(cfg, processor, None)
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [(b"1", b"email-1")]
            MockImap.return_value = mock_conn
            await poller.poll_once()
            mock_conn.connect.assert_called_once()
            mock_conn.fetch_unseen.assert_called_once()
            processor.process_batch.assert_awaited_once_with([b"email-1"])
            mock_conn.mark_seen.assert_called_once_with(b"1")
            mock_conn.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_once_does_not_mark_seen_on_failure(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(
            return_value=[
                ProcessResult(
                    success=False, should_reply=False, body="", job_id="job-1"
                )
            ]
        )
        poller = EmailPoller(cfg, processor, None)
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [(b"1", b"email-1")]
            MockImap.return_value = mock_conn
            await poller.poll_once()
            processor.process_batch.assert_awaited_once_with([b"email-1"])
            mock_conn.mark_seen.assert_not_called()
            mock_conn.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_once_marks_seen_on_terminal_failure_reply(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(
            return_value=[
                ProcessResult(
                    success=False,
                    should_reply=True,
                    body="",
                    job_id="job-1",
                )
            ]
        )
        mock_job = MagicMock()
        mock_job.status = JobStatus.FAILED
        processor.store.get_job.return_value = mock_job
        poller = EmailPoller(cfg, processor, None)
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [(b"1", b"email-1")]
            MockImap.return_value = mock_conn
            await poller.poll_once()
            processor.process_batch.assert_awaited_once_with([b"email-1"])
            processor.store.get_job.assert_called_once_with("job-1")
            mock_conn.mark_seen.assert_called_once_with(b"1")
            mock_conn.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_once_marks_seen_on_quarantined_failure_reply(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(
            return_value=[
                ProcessResult(
                    success=False,
                    should_reply=True,
                    body="",
                    job_id="job-1",
                )
            ]
        )
        mock_job = MagicMock()
        mock_job.status = JobStatus.QUARANTINED
        processor.store.get_job.return_value = mock_job
        poller = EmailPoller(cfg, processor, None)
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [(b"1", b"email-1")]
            MockImap.return_value = mock_conn
            await poller.poll_once()
            mock_conn.mark_seen.assert_called_once_with(b"1")

    @pytest.mark.asyncio
    async def test_poll_once_does_not_mark_seen_on_non_terminal_failure_reply(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(
            return_value=[
                ProcessResult(
                    success=False,
                    should_reply=True,
                    body="",
                    job_id="job-1",
                )
            ]
        )
        mock_job = MagicMock()
        mock_job.status = JobStatus.ANALYSING
        processor.store.get_job.return_value = mock_job
        poller = EmailPoller(cfg, processor, None)
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [(b"1", b"email-1")]
            MockImap.return_value = mock_conn
            await poller.poll_once()
            mock_conn.mark_seen.assert_not_called()
            mock_conn.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_poll_once_with_injected_client_does_not_disconnect(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(return_value=[])
        injected_client = MagicMock()
        injected_client.fetch_unseen.return_value = []
        poller = EmailPoller(cfg, processor, injected_client)
        await poller.poll_once()
        injected_client.disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_poll_once_raises_on_result_count_mismatch(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(return_value=[])  # fewer results than emails
        poller = EmailPoller(cfg, processor, None)
        with patch("services.email_poller.ImapClient") as MockImap:
            mock_conn = MagicMock()
            mock_conn.fetch_unseen.return_value = [(b"1", b"email-1")]
            MockImap.return_value = mock_conn
            with pytest.raises(RuntimeError):
                await poller.poll_once()

    @pytest.mark.asyncio
    async def test_run_loop_can_be_stopped(self, cfg):
        processor = MagicMock()
        processor.process_batch = AsyncMock(return_value=[])
        poller = EmailPoller(cfg, processor, MagicMock())
        poller.imap_client.fetch_unseen.return_value = []
        task = asyncio.create_task(poller.run())
        await asyncio.sleep(0.05)
        poller.stop()
        await task
        assert poller._stop_event.is_set()
