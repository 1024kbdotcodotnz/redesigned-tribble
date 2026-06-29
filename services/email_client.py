"""IMAP/SMTP clients for the email bridge."""
import imaplib
import logging
import smtplib
from email import message_from_bytes
from email.message import EmailMessage
from email.utils import parseaddr
from typing import List, Tuple

from services.email_config import EmailConfig

logger = logging.getLogger(__name__)

# Stable reference to the real IMAP4 error class so tests that patch
# services.email_client.imaplib still catch a genuine exception.
_IMAP4_ERROR = imaplib.IMAP4.error


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
            except (AttributeError, _IMAP4_ERROR) as exc:
                logger.warning("IMAP STARTTLS not available or failed: %s", exc)
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

    def fetch_unseen(self) -> List[Tuple[bytes, bytes]]:
        if not self._conn:
            raise RuntimeError("IMAP not connected")
        status, messages = self._conn.search(None, "UNSEEN")
        if status != "OK":
            return []
        msg_ids = messages[0].split()
        results: List[Tuple[bytes, bytes]] = []
        for msg_id in msg_ids:
            status, data = self._conn.fetch(msg_id, "(RFC822)")
            if status == "OK" and data:
                first = data[0]
                if isinstance(first, tuple) and len(first) == 2:
                    results.append((msg_id, first[1]))
        return results

    def mark_seen(self, msg_id: bytes) -> None:
        if self._conn:
            self._conn.store(msg_id, "+FLAGS", "\\Seen")


class SmtpClient:
    def __init__(self, config: EmailConfig):
        self.config = config

    def check_connection(self) -> None:
        """Verify SMTP connectivity by logging in without sending mail."""
        if self.config.smtp_use_tls:
            if self.config.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    self.config.smtp_host, self.config.smtp_port, timeout=10
                ) as server:
                    server.login(self.config.smtp_username, self.config.smtp_password)
            else:
                with smtplib.SMTP(
                    self.config.smtp_host, self.config.smtp_port, timeout=10
                ) as server:
                    server.starttls()
                    server.login(self.config.smtp_username, self.config.smtp_password)
        else:
            with smtplib.SMTP(
                self.config.smtp_host, self.config.smtp_port, timeout=10
            ) as server:
                server.login(self.config.smtp_username, self.config.smtp_password)

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
        if attachment_bytes:
            msg.add_attachment(
                attachment_bytes,
                maintype="application",
                subtype="octet-stream",
                filename=attachment_filename,
            )
        if self.config.smtp_use_tls:
            if self.config.smtp_port == 465:
                with smtplib.SMTP_SSL(
                    self.config.smtp_host, self.config.smtp_port, timeout=30
                ) as server:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(
                    self.config.smtp_host, self.config.smtp_port, timeout=30
                ) as server:
                    server.starttls()
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    server.send_message(msg)
        else:
            with smtplib.SMTP(
                self.config.smtp_host, self.config.smtp_port, timeout=30
            ) as server:
                server.login(self.config.smtp_username, self.config.smtp_password)
                server.send_message(msg)


def extract_sender_address(raw_email: bytes) -> str:
    msg = message_from_bytes(raw_email)
    from_header = msg.get("From", "")
    _, addr = parseaddr(from_header)
    return addr
