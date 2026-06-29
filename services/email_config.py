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
