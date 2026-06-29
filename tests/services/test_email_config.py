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
