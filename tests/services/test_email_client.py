import imaplib
import io
from unittest.mock import MagicMock, patch
import pytest
from services.email_client import ImapClient, SmtpClient, extract_sender_address
from services.email_config import EmailConfig


def make_email_config(**overrides):
    defaults = {
        "enabled": True,
        "imap_host": "imap.example.com",
        "imap_port": 993,
        "imap_use_ssl": True,
        "imap_username": "user",
        "imap_password": "pass",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_use_tls": True,
        "smtp_username": "user",
        "smtp_password": "pass",
        "inbox_name": "INBOX",
        "poll_interval_seconds": 60,
        "max_retries": 3,
        "sender_daily_limit": 10,
        "max_attachment_bytes": 25 * 1024 * 1024,
        "dry_run": False,
        "system_tenant_id": "system_email",
    }
    defaults.update(overrides)
    return EmailConfig(**defaults)


class TestImapClient:
    @pytest.fixture
    def cfg(self):
        return make_email_config()

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
        assert messages[0] == (b"1", b"raw-email-1")
        client.mark_seen(b"1")
        mock_conn.store.assert_called_once()

    @patch("services.email_client.imaplib")
    def test_connect_without_ssl_uses_starttls(self, mock_imaplib, cfg):
        cfg = make_email_config(imap_use_ssl=False)
        mock_conn = MagicMock()
        mock_imaplib.IMAP4.return_value = mock_conn
        client = ImapClient(cfg)
        client.connect()
        mock_imaplib.IMAP4.assert_called_once_with(cfg.imap_host, cfg.imap_port)
        mock_conn.starttls.assert_called_once()
        mock_conn.login.assert_called_once_with(cfg.imap_username, cfg.imap_password)
        mock_conn.select.assert_called_once_with(cfg.inbox_name)

    @patch("services.email_client.imaplib")
    def test_connect_without_ssl_falls_back_to_plaintext_on_starttls_failure(
        self, mock_imaplib, cfg
    ):
        cfg = make_email_config(imap_use_ssl=False)
        mock_conn = MagicMock()
        mock_conn.starttls.side_effect = imaplib.IMAP4.error("STARTTLS not supported")
        mock_imaplib.IMAP4.return_value = mock_conn
        client = ImapClient(cfg)
        client.connect()
        mock_conn.starttls.assert_called_once()
        mock_conn.login.assert_called_once_with(cfg.imap_username, cfg.imap_password)
        mock_conn.select.assert_called_once_with(cfg.inbox_name)

    @patch("services.email_client.imaplib")
    def test_disconnect_closes_connection(self, mock_imaplib, cfg):
        mock_conn = MagicMock()
        mock_imaplib.IMAP4_SSL.return_value = mock_conn
        client = ImapClient(cfg)
        client.connect()
        client.disconnect()
        mock_conn.close.assert_called_once()
        mock_conn.logout.assert_called_once()
        assert client._conn is None


class TestSmtpClient:
    @pytest.fixture
    def cfg(self):
        return make_email_config()

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
        mock_smtplib.SMTP.assert_called_once_with(
            cfg.smtp_host, cfg.smtp_port, timeout=30
        )
        mock_conn.send_message.assert_called_once()

    def test_send_reply_dry_run_is_no_op(self, cfg):
        cfg = make_email_config(dry_run=True)
        client = SmtpClient(cfg)
        # Should not raise or attempt any SMTP connection.
        client.send_reply(
            to_address="client@example.com",
            subject="RE: Disclosure",
            body="See attached.",
            attachment_bytes=b"docx-bytes",
            attachment_filename="report.docx",
        )

    @patch("services.email_client.smtplib")
    def test_send_reply_without_tls_uses_plain_smtp(self, mock_smtplib, cfg):
        cfg = make_email_config(smtp_use_tls=False)
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
        mock_smtplib.SMTP_SSL.assert_not_called()
        mock_smtplib.SMTP.assert_called_once_with(
            cfg.smtp_host, cfg.smtp_port, timeout=30
        )
        mock_conn.starttls.assert_not_called()
        mock_conn.login.assert_called_once_with(cfg.smtp_username, cfg.smtp_password)
        mock_conn.send_message.assert_called_once()

    @patch("services.email_client.smtplib")
    def test_send_reply_port_465_uses_smtp_ssl(self, mock_smtplib, cfg):
        cfg = make_email_config(smtp_port=465)
        mock_conn = MagicMock()
        mock_smtplib.SMTP_SSL.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_smtplib.SMTP_SSL.return_value.__exit__ = MagicMock(return_value=False)
        client = SmtpClient(cfg)
        client.send_reply(
            to_address="client@example.com",
            subject="RE: Disclosure",
            body="See attached.",
            attachment_bytes=b"docx-bytes",
            attachment_filename="report.docx",
        )
        mock_smtplib.SMTP.assert_not_called()
        mock_smtplib.SMTP_SSL.assert_called_once_with(
            cfg.smtp_host, cfg.smtp_port, timeout=30
        )
        mock_conn.starttls.assert_not_called()
        mock_conn.login.assert_called_once_with(cfg.smtp_username, cfg.smtp_password)
        mock_conn.send_message.assert_called_once()

    @patch("services.email_client.smtplib")
    def test_check_connection_port_465_uses_smtp_ssl(self, mock_smtplib, cfg):
        cfg = make_email_config(smtp_port=465)
        mock_conn = MagicMock()
        mock_smtplib.SMTP_SSL.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_smtplib.SMTP_SSL.return_value.__exit__ = MagicMock(return_value=False)
        client = SmtpClient(cfg)
        client.check_connection()
        mock_smtplib.SMTP.assert_not_called()
        mock_smtplib.SMTP_SSL.assert_called_once_with(
            cfg.smtp_host, cfg.smtp_port, timeout=10
        )
        mock_conn.starttls.assert_not_called()
        mock_conn.login.assert_called_once_with(cfg.smtp_username, cfg.smtp_password)

    @patch("services.email_client.smtplib")
    def test_check_connection_port_587_uses_starttls(self, mock_smtplib, cfg):
        mock_conn = MagicMock()
        mock_smtplib.SMTP.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_smtplib.SMTP.return_value.__exit__ = MagicMock(return_value=False)
        client = SmtpClient(cfg)
        client.check_connection()
        mock_smtplib.SMTP_SSL.assert_not_called()
        mock_smtplib.SMTP.assert_called_once_with(
            cfg.smtp_host, cfg.smtp_port, timeout=10
        )
        mock_conn.starttls.assert_called_once()
        mock_conn.login.assert_called_once_with(cfg.smtp_username, cfg.smtp_password)

    @patch("services.email_client.smtplib")
    def test_check_connection_plain_smtp_when_tls_disabled(self, mock_smtplib, cfg):
        cfg = make_email_config(smtp_use_tls=False)
        mock_conn = MagicMock()
        mock_smtplib.SMTP.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_smtplib.SMTP.return_value.__exit__ = MagicMock(return_value=False)
        client = SmtpClient(cfg)
        client.check_connection()
        mock_smtplib.SMTP_SSL.assert_not_called()
        mock_smtplib.SMTP.assert_called_once_with(
            cfg.smtp_host, cfg.smtp_port, timeout=10
        )
        mock_conn.starttls.assert_not_called()
        mock_conn.login.assert_called_once_with(cfg.smtp_username, cfg.smtp_password)


def test_extract_sender_address_parses_from_header():
    raw_email = (
        b"From: John Doe <john.doe@example.com>\r\n"
        b"To: support@example.com\r\n"
        b"Subject: Hello\r\n\r\n"
        b"Body"
    )
    assert extract_sender_address(raw_email) == "john.doe@example.com"
